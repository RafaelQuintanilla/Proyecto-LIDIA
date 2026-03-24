"""
SINIA-SA — Transformación de Datos MODIS MCD12Q1 (Cobertura Vegetal)
=====================================================================
Limpia y normaliza los datos crudos de clasificación IGBP descargados
por extract_modis.py desde la API de NASA AppEEARS.

Pasos:
    1. Validación de clasificación IGBP (1-17, 255=sin dato)
    2. Agrupación por combustibilidad (alto/medio/bajo riesgo de incendio)
    3. Normalización al esquema del proyecto
    4. Guardado como Parquet en data/processed/modis_lc.parquet
"""

from __future__ import annotations
from pathlib import Path

import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from config.settings import DIR_PROCESADO
from etl.utils.logger import setup_logger

logger = setup_logger("sinia.transform.modis")

# Mapeo IGBP -> nivel de combustibilidad para incendios
# Alto: vegetación densa con alta carga de combustible
# Medio: vegetación mixta o degradada
# Bajo: urbano, agua, nieve, suelo desnudo
COMBUSTIBILIDAD = {
    1:  "alto",    # Bosque siempreverde de coníferas
    2:  "alto",    # Bosque caducifolio de coníferas
    3:  "alto",    # Bosque siempreverde de hoja ancha (amazonia, selva)
    4:  "alto",    # Bosque caducifolio de hoja ancha
    5:  "alto",    # Bosque mixto
    6:  "medio",   # Arbustal cerrado
    7:  "medio",   # Arbustal abierto
    8:  "medio",   # Sabana arbolada (cerrado brasileño)
    9:  "alto",    # Sabana — alta carga de pasto seco
    10: "alto",    # Pastizal — combustible fino, rápida propagación
    11: "bajo",    # Humedal permanente — difícilmente inflamable
    12: "medio",   # Tierra de cultivo — depende de residuos
    13: "bajo",    # Zona urbana
    14: "medio",   # Cultivo/Vegetación natural mosaico
    15: "bajo",    # Nieve y hielo
    16: "bajo",    # Suelo desnudo / Vegetación escasa
    17: "bajo",    # Cuerpo de agua
    255: None,     # Sin clasificar
}

IGBP_LABELS = {
    1: "Bosque siempreverde coníferas",
    2: "Bosque caducifolio coníferas",
    3: "Bosque siempreverde hoja ancha",
    4: "Bosque caducifolio hoja ancha",
    5: "Bosque mixto",
    6: "Arbustal cerrado",
    7: "Arbustal abierto",
    8: "Sabana arbolada",
    9: "Sabana",
    10: "Pastizal",
    11: "Humedal permanente",
    12: "Tierra de cultivo",
    13: "Zona urbana",
    14: "Cultivo/Vegetación mosaico",
    15: "Nieve y hielo",
    16: "Suelo desnudo",
    17: "Cuerpo de agua",
    255: "Sin clasificar",
}


def transformar_modis(df: pd.DataFrame, guardar: bool = True) -> pd.DataFrame:
    """
    Transforma datos crudos de clasificación MODIS MCD12Q1.

    Args:
        df:      DataFrame con columnas: punto, pais, anio, lc_type1, lc_descripcion, fuente
        guardar: Si True, acumula en data/processed/modis_lc.parquet

    Returns:
        DataFrame enriquecido con columna adicional: combustibilidad
    """
    if df.empty:
        logger.warning("transformar_modis: DataFrame vacío")
        return df

    cantidad_original = len(df)
    logger.info(
        f"Iniciando transformación MODIS: {cantidad_original} registros",
        extra={"etl_stage": "transform", "source": "modis"},
    )

    df = df.copy()

    # ── Paso 1: Tipos de datos ────────────────────────────────────────────────
    df["anio"]     = pd.to_numeric(df["anio"],     errors="coerce").astype("Int64")
    df["lc_type1"] = pd.to_numeric(df["lc_type1"], errors="coerce").fillna(255).astype(int)

    # Validar rango IGBP
    df = df[df["lc_type1"].isin(list(range(1, 18)) + [255])]

    # ── Paso 2: Enriquecer con descripción y combustibilidad ──────────────────
    df["lc_descripcion"]  = df["lc_type1"].map(IGBP_LABELS).fillna("Sin clasificar")
    df["combustibilidad"] = df["lc_type1"].map(COMBUSTIBILIDAD)

    # ── Paso 3: Eliminar duplicados ───────────────────────────────────────────
    antes = len(df)
    df = df.drop_duplicates(subset=["punto", "anio"])
    if antes - len(df) > 0:
        logger.info(f"  Eliminados {antes - len(df)} duplicados (punto, anio)")

    cantidad_final = len(df)
    logger.info(
        f"Transformación MODIS: {cantidad_original} -> {cantidad_final} registros",
        extra={"etl_stage": "transform", "source": "modis", "rows_count": cantidad_final},
    )

    if guardar and not df.empty:
        ruta = DIR_PROCESADO / "modis_lc.parquet"
        if ruta.exists():
            df_prev = pd.read_parquet(ruta)
            df = pd.concat([df_prev, df], ignore_index=True).drop_duplicates(
                subset=["punto", "anio"]
            )
        ruta.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(ruta, index=False)
        logger.info(f"Parquet guardado en: {ruta} ({len(df)} registros totales)")

    return df


if __name__ == "__main__":
    ruta_raw = DIR_PROCESADO.parent / "raw" / "modis"
    archivos = list(ruta_raw.glob("modis_lc_*.csv")) if ruta_raw.exists() else []

    print("=" * 60)
    print("SINIA-SA — Transformación MODIS Land Cover")
    print("=" * 60)

    if not archivos:
        print(
            "No hay archivos en data/raw/modis/.\n"
            "Ejecutá primero extract_modis.py (requiere cuenta NASA Earthdata en .env)"
        )
    else:
        frames = [pd.read_csv(f) for f in archivos]
        df_crudo = pd.concat(frames, ignore_index=True)
        print(f"\nProcesando {len(df_crudo)} registros crudos...")
        df_procesado = transformar_modis(df_crudo)
        print(f"Registros procesados: {len(df_procesado)}")
        if not df_procesado.empty:
            print(df_procesado.groupby("combustibilidad").size())
