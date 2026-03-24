"""
SINIA-SA — Sincronización histórica PostgreSQL → MongoDB
=========================================================
Lee focos_calor de PostgreSQL año a año y genera:
  1. focos_snapshots  — un documento por día con resumen + top 500 focos por FRP
  2. ejecuciones_etl  — audit trail de la sincronización

Los snapshots NO guardan todos los focos (para evitar el límite 16MB de Mongo),
sino el resumen estadístico + los 500 focos de mayor potencia radiativa del día.
Los datos completos siguen en PostgreSQL para queries analíticas.

Uso:
  python etl/sincronizar_mongo_historico.py          # 2018-2023
  python etl/sincronizar_mongo_historico.py 2021     # solo 2021
  python etl/sincronizar_mongo_historico.py 2021 2022
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import decimal

import pandas as pd
import psycopg2
import psycopg2.extras

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import PG_CONFIG
from etl.load.load_mongo import (
    crear_colecciones_con_schema,
    get_db,
    registrar_ejecucion_etl,
)
from etl.utils.logger import setup_logger

logger = setup_logger("sinia.sync_mongo")


def _safe(v):
    """Convierte tipos PG/numpy a tipos nativos Python para MongoDB."""
    import numpy as np
    if v is None:
        return None
    if isinstance(v, decimal.Decimal):
        return float(v)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return None if np.isnan(v) else float(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, float) and (v != v):  # NaN check
        return None
    return v


TOP_FOCOS_POR_DIA = 500   # máx focos embebidos por snapshot (evita límite 16MB)
BATCH_DIAS = 30           # días procesados por query a PG


def _get_pg_conn():
    conn = psycopg2.connect(
        host=PG_CONFIG["host"],
        port=PG_CONFIG["port"],
        dbname=PG_CONFIG["database"],
        user=PG_CONFIG["user"],
        password=PG_CONFIG["password"],
    )
    # Convertir automáticamente NUMERIC/DECIMAL → float en todos los resultados
    dec2float = psycopg2.extensions.new_type(
        psycopg2.extensions.DECIMAL.values,
        "DEC2FLOAT",
        lambda val, cur: float(val) if val is not None else None,
    )
    psycopg2.extensions.register_type(dec2float, conn)
    return conn


def _sincronizar_anio(anio: int) -> dict:
    """Sincroniza un año completo de focos_calor → MongoDB focos_snapshots."""
    db = get_db()
    col_snap = db["focos_snapshots"]

    conn = _get_pg_conn()
    t0 = time.perf_counter()
    snapshots_ok = 0
    snapshots_err = 0
    total_focos = 0

    try:
        # Obtener todos los días con focos en ese año
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT fecha_adq
                FROM focos_calor
                WHERE fecha_adq >= %s AND fecha_adq < %s
                ORDER BY fecha_adq
                """,
                (f"{anio}-01-01", f"{anio + 1}-01-01"),
            )
            fechas = [row[0] for row in cur.fetchall()]

        logger.info(f"[{anio}] {len(fechas)} días con focos encontrados en PG")

        for fecha in fechas:
            try:
                # Top 500 focos del día por potencia radiativa
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT
                            latitud, longitud, hora_adq_hhmm,
                            potencia_radiativa, confianza_raw, confianza_num,
                            satelite, es_diurno, pais
                        FROM focos_calor
                        WHERE fecha_adq = %s
                        ORDER BY potencia_radiativa DESC NULLS LAST
                        LIMIT %s
                        """,
                        (fecha, TOP_FOCOS_POR_DIA),
                    )
                    top_focos = cur.fetchall()

                    # Resumen estadístico del día completo
                    cur.execute(
                        """
                        SELECT
                            COUNT(*)                             AS total,
                            AVG(potencia_radiativa)              AS frp_promedio,
                            MAX(potencia_radiativa)              AS frp_maximo,
                            SUM(CASE WHEN confianza_num = 3 THEN 1 ELSE 0 END) AS alta_confianza,
                            SUM(CASE WHEN es_diurno THEN 1 ELSE 0 END)         AS diurnos,
                            SUM(CASE WHEN NOT es_diurno THEN 1 ELSE 0 END)     AS nocturnos
                        FROM focos_calor
                        WHERE fecha_adq = %s
                        """,
                        (fecha,),
                    )
                    stats = cur.fetchone()

                    # Focos por país ese día
                    cur.execute(
                        """
                        SELECT pais, COUNT(*) as n
                        FROM focos_calor
                        WHERE fecha_adq = %s
                        GROUP BY pais
                        ORDER BY n DESC
                        """,
                        (fecha,),
                    )
                    por_pais = {row["pais"]: int(row["n"]) for row in cur.fetchall()}

                total_dia = int(stats["total"])
                total_focos += total_dia

                focos_lista = [
                    {
                        "latitud":            _safe(r["latitud"]),
                        "longitud":           _safe(r["longitud"]),
                        "hora_adq_hhmm":      _safe(r["hora_adq_hhmm"]),
                        "potencia_radiativa": _safe(r["potencia_radiativa"]),
                        "confianza_raw":      _safe(r["confianza_raw"]),
                        "confianza_num":      _safe(r["confianza_num"]),
                        "satelite":           _safe(r["satelite"]),
                        "es_diurno":          _safe(r["es_diurno"]),
                        "pais":               _safe(r["pais"]),
                    }
                    for r in top_focos
                ]

                fecha_dt = datetime(fecha.year, fecha.month, fecha.day, tzinfo=timezone.utc)

                doc = {
                    "fecha":           fecha_dt,
                    "generado_en":     datetime.now(timezone.utc),
                    "total_focos":     total_dia,
                    "focos_en_doc":    len(focos_lista),  # puede ser < total si hay más de TOP
                    "resumen": {
                        "frp_promedio":         float(stats["frp_promedio"]) if stats["frp_promedio"] else None,
                        "frp_maximo":           float(stats["frp_maximo"])   if stats["frp_maximo"]   else None,
                        "focos_alta_confianza": int(stats["alta_confianza"]),
                        "focos_diurnos":        int(stats["diurnos"]),
                        "focos_nocturnos":      int(stats["nocturnos"]),
                        "por_pais":             por_pais,
                    },
                    "focos": focos_lista,
                }

                col_snap.replace_one({"fecha": fecha_dt}, doc, upsert=True)
                snapshots_ok += 1

            except Exception as e:
                logger.warning(f"[{anio}] Error en snapshot {fecha}: {e}")
                snapshots_err += 1

        duracion = time.perf_counter() - t0
        logger.info(
            f"[{anio}] Sincronización completada — "
            f"{snapshots_ok} snapshots OK, {snapshots_err} errores, "
            f"{total_focos:,} focos totales — {duracion:.1f}s"
        )
        return {
            "snapshots_ok": snapshots_ok,
            "snapshots_err": snapshots_err,
            "total_focos": total_focos,
            "duracion": duracion,
        }

    finally:
        conn.close()


def ejecutar_sync(anio_inicio: int = 2018, anio_fin: int = 2023) -> None:
    print(f"\n{'='*60}")
    print(f"SINIA-SA — Sync MongoDB histórico {anio_inicio}–{anio_fin}")
    print(f"{'='*60}\n")

    # Asegurar colecciones e índices
    crear_colecciones_con_schema()

    total_global = {"snapshots": 0, "focos": 0}

    for anio in range(anio_inicio, anio_fin + 1):
        print(f"\n--- AÑO {anio} ---")
        t0 = time.perf_counter()
        try:
            res = _sincronizar_anio(anio)
            total_global["snapshots"] += res["snapshots_ok"]
            total_global["focos"]     += res["total_focos"]

            registrar_ejecucion_etl(
                fuente="firms",
                etapa="load",
                tipo_carga="historico",
                estado="ok",
                metricas={
                    "anio": anio,
                    "snapshots_generados": res["snapshots_ok"],
                    "focos_procesados": res["total_focos"],
                },
                duracion_segundos=res["duracion"],
            )
            print(f"  OK — {res['snapshots_ok']} días, {res['total_focos']:,} focos ({res['duracion']:.1f}s)")

        except Exception as e:
            duracion = time.perf_counter() - t0
            logger.error(f"Error en año {anio}: {e}", exc_info=True)
            registrar_ejecucion_etl(
                fuente="firms",
                etapa="load",
                tipo_carga="historico",
                estado="error",
                mensaje=str(e),
                duracion_segundos=duracion,
            )
            print(f"  ERROR en {anio}: {e}")

    print(f"\n{'='*60}")
    print(f"Sync completado: {total_global['snapshots']} snapshots, {total_global['focos']:,} focos")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) == 2:
        ini, fin = int(args[0]), int(args[1])
    elif len(args) == 1:
        ini = fin = int(args[0])
    else:
        ini, fin = 2018, 2023

    ejecutar_sync(ini, fin)
