"""
SINIA-SA — Transformación de Datos CHIRPS (Precipitación Mensual)
=================================================================
Limpia y normaliza los datos crudos de precipitación CHIRPS descargados
por extract_chirps.py desde la API de ClimateSERV.

Pasos:
    1. Validación de rango (precipitación >= 0, fechas válidas)
    2. Normalización de columnas al esquema del proyecto
    3. Clasificación de anomalía de precipitación (% vs promedio mensual)
    4. Guardado como Parquet en data/processed/chirps_sa.parquet
"""

from __future__ import annotations
from pathlib import Path

import pandas as pd
import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from config.settings import DIR_PROCESADO
from etl.utils.logger import setup_logger

logger = setup_logger("sinia.transform.chirps")

# Umbral para clasificar déficit hídrico: <60% del promedio mensual histórico
UMBRAL_DEFICIT = 0.60


def transformar_chirps(df: pd.DataFrame, guardar: bool = True) -> pd.DataFrame:
    """
    Transforma datos crudos de precipitación CHIRPS.

    Args:
        df:      DataFrame con columnas: punto, pais, fecha, precipitacion_mm, fuente
        guardar: Si True, acumula en data/processed/chirps_sa.parquet

    Returns:
        DataFrame enriquecido con columnas adicionales:
        anio, mes, anio_mes, precipitacion_anomalia_pct, deficit_hidrico
    """
    if df.empty:
        logger.warning("transformar_chirps: DataFrame vacío")
        return df

    cantidad_original = len(df)
    logger.info(
        f"Iniciando transformación CHIRPS: {cantidad_original} registros",
        extra={"etl_stage": "transform", "source": "chirps"},
    )

    df = df.copy()

    # ── Paso 1: Tipos de datos ────────────────────────────────────────────────
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df["precipitacion_mm"] = pd.to_numeric(df["precipitacion_mm"], errors="coerce")

    # Eliminar filas con fecha o precipitación inválida
    antes = len(df)
    df = df.dropna(subset=["fecha", "precipitacion_mm"])
    df = df[df["precipitacion_mm"] >= 0]
    eliminados = antes - len(df)
    if eliminados > 0:
        logger.warning(f"  Eliminados {eliminados} registros con datos inválidos")

    if df.empty:
        logger.warning("transformar_chirps: sin registros válidos tras limpieza")
        return df

    # ── Paso 2: Columnas derivadas ────────────────────────────────────────────
    df["anio"]     = df["fecha"].dt.year
    df["mes"]      = df["fecha"].dt.month
    df["anio_mes"] = df["fecha"].dt.to_period("M").astype(str)

    # ── Paso 3: Anomalía de precipitación por punto y mes ────────────────────
    # Calculamos el promedio histórico de cada mes (ej: enero) por punto
    # La anomalía es (valor - promedio) / promedio — normalizada como porcentaje
    promedio_mensual = (
        df.groupby(["punto", "mes"])["precipitacion_mm"]
        .transform("mean")
    )

    df["precipitacion_anomalia_pct"] = (
        (df["precipitacion_mm"] - promedio_mensual) / promedio_mensual.replace(0, np.nan)
    ).round(4)

    # Déficit hídrico: True si el mes tiene menos del UMBRAL_DEFICIT del promedio
    df["deficit_hidrico"] = df["precipitacion_mm"] < (promedio_mensual * UMBRAL_DEFICIT)

    # ── Paso 4: Eliminar duplicados ───────────────────────────────────────────
    antes = len(df)
    df = df.drop_duplicates(subset=["punto", "anio", "mes"])
    if antes - len(df) > 0:
        logger.info(f"  Eliminados {antes - len(df)} duplicados (punto, anio, mes)")

    cantidad_final = len(df)
    logger.info(
        f"Transformación CHIRPS: {cantidad_original} -> {cantidad_final} registros",
        extra={"etl_stage": "transform", "source": "chirps", "rows_count": cantidad_final},
    )

    if guardar and not df.empty:
        ruta = DIR_PROCESADO / "chirps_sa.parquet"
        # Acumular con datos previos
        if ruta.exists():
            df_prev = pd.read_parquet(ruta)
            df = pd.concat([df_prev, df], ignore_index=True).drop_duplicates(
                subset=["punto", "anio", "mes"]
            )
        ruta.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(ruta, index=False)
        logger.info(f"Parquet guardado en: {ruta} ({len(df)} registros totales)")

    return df


if __name__ == "__main__":
    ruta_raw = DIR_PROCESADO.parent / "raw" / "chirps"
    archivos = list(ruta_raw.glob("chirps_*.csv")) if ruta_raw.exists() else []

    print("=" * 60)
    print("SINIA-SA — Transformación CHIRPS Precipitación")
    print("=" * 60)

    if not archivos:
        print("No hay archivos en data/raw/chirps/. Ejecutá primero extract_chirps.py")
    else:
        frames = [pd.read_csv(f) for f in archivos]
        df_crudo = pd.concat(frames, ignore_index=True)
        print(f"\nProcesando {len(df_crudo)} registros crudos...")
        df_procesado = transformar_chirps(df_crudo)
        print(f"Registros procesados: {len(df_procesado)}")
        if not df_procesado.empty:
            print(df_procesado.head().to_string())
