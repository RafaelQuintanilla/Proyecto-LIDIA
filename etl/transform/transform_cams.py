# =============================================================================
# SINIA-UY — Transformación de Datos CAMS (Calidad del Aire)
# =============================================================================
# Este módulo procesa los datos horarios de calidad del aire de CAMS y los
# transforma en datos diarios listos para análisis y visualización.
#
# Transformaciones principales:
#   1. Los datos crudos son HORARIOS (una fila por hora)
#   2. Los transformamos en DIARIOS (una fila por día) mediante agregación
#   3. Calculamos media, máximo y percentil 95 de PM10 por día
#   4. Aplicamos el umbral de la OMS para alertas de salud pública
#
# Umbral OMS para PM10 (Guía 2021):
#   - Media diaria: 45 µg/m³ (microgramos por metro cúbico)
#   - Superarlo indica riesgo para la salud, especialmente en zonas de incendio
# =============================================================================

from pathlib import Path

import pandas as pd
import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from config.settings import DIR_PROCESADO
from etl.utils.logger import setup_logger

logger = setup_logger("sinia.transform.cams")

# -----------------------------------------------------------------------------
# UMBRALES DE REFERENCIA PARA PM10
# Basados en las Guías de Calidad del Aire de la OMS (2021)
# -----------------------------------------------------------------------------

PM10_OMS_DIARIO = 45.0    # µg/m³ — límite OMS para media diaria de PM10
PM10_ALERTA     = 100.0   # µg/m³ — nivel de alerta sanitaria (supera doble del límite OMS)


# =============================================================================
# FUNCIÓN PRINCIPAL DE TRANSFORMACIÓN
# =============================================================================

def transformar_cams(df: pd.DataFrame, guardar: bool = True) -> pd.DataFrame:
    """
    Transforma datos CAMS horarios en datos diarios con agregaciones y alertas.

    Pasos de transformación:
    1. Casteo de tipos (string -> datetime, string -> float)
    2. Extracción de la fecha (sin hora) para la agrupación diaria
    3. Detección y reporte de nulos en PM10 y PM2.5
    4. Agregación horaria -> diaria: media, máximo y percentil 95
    5. Clasificación del nivel de PM10 según umbral OMS

    Args:
        df:       DataFrame crudo de Open-Meteo Air Quality (granularidad hourly)
        guardar:  Si True, guarda el resultado como Parquet en data/processed/

    Returns:
        DataFrame diario con columnas:
        - fecha:           Fecha del día
        - punto:           Nombre del punto de monitoreo
        - pm10_media:      Media diaria de PM10 (µg/m³)
        - pm10_max:        Máximo horario de PM10 en el día
        - pm10_p95:        Percentil 95 de PM10 (casi el máximo, sin outliers)
        - pm2_5_media:     Media diaria de PM2.5 (µg/m³)
        - european_aqi_media: Media diaria del AQI europeo
        - supera_oms_pm10: True/False si la media supera 45 µg/m³
        - nivel_pm10:      "normal", "elevado" o "alerta"
    """
    if df.empty:
        logger.warning("transformar_cams: DataFrame vacío, sin datos para transformar")
        return df

    cantidad_original = len(df)

    logger.info(
        f"Iniciando transformación CAMS: {cantidad_original} registros horarios",
        extra={"etl_stage": "transform", "source": "cams"},
    )

    # Hacemos una copia para no modificar el DataFrame original
    df = df.copy()

    # ── Paso 1: Casteo de tipos ───────────────────────────────────────────────

    # Convertimos fecha_hora de string a datetime
    # Ejemplo: "2024-01-15T14:00" -> Timestamp('2024-01-15 14:00:00')
    df["fecha_hora"] = pd.to_datetime(df["fecha_hora"], errors="coerce")

    # Extraemos solo la fecha (sin hora) para poder agrupar por día
    # Ejemplo: Timestamp('2024-01-15 14:00:00') -> date(2024, 1, 15)
    df["fecha"] = df["fecha_hora"].dt.date

    # Convertimos todas las variables de calidad del aire a numérico
    columnas_numericas = [
        "pm10",                   # Material particulado ≤10µm
        "pm2_5",                  # Material particulado ≤2.5µm
        "aerosol_optical_depth",  # Profundidad óptica de aerosoles
        "dust",                   # Polvo mineral
        "european_aqi",           # Índice de calidad del aire europeo
        "european_aqi_pm10",      # AQI solo por PM10
        "european_aqi_pm2_5",     # AQI solo por PM2.5
    ]

    for columna in columnas_numericas:
        if columna in df.columns:
            df[columna] = pd.to_numeric(df[columna], errors="coerce")

    # ── Paso 2: Detección de nulos ────────────────────────────────────────────

    for columna in ["pm10", "pm2_5"]:
        if columna in df.columns:
            cantidad_nulos = df[columna].isna().sum()
            if cantidad_nulos > 0:
                logger.warning(
                    f"  {columna}: {cantidad_nulos} valores nulos "
                    f"({cantidad_nulos / cantidad_original * 100:.1f}%)",
                    extra={"etl_stage": "transform", "source": "cams"},
                )

    # ── Paso 3: Agregación horaria -> diaria ──────────────────────────────────
    # Agrupamos por fecha y punto (si existe) para calcular estadísticas diarias

    # Determinamos las columnas de agrupación
    columnas_grupo = ["fecha", "punto"] if "punto" in df.columns else ["fecha"]

    # Construimos el diccionario de agregaciones usando NamedAgg para claridad
    # Cada clave es el nombre de la nueva columna, el valor define cómo calcularlo
    diccionario_agg = {}

    # Para PM10: calculamos media, máximo y percentil 95
    if "pm10" in df.columns:
        diccionario_agg["pm10_media"] = pd.NamedAgg(column="pm10", aggfunc="mean")
        diccionario_agg["pm10_max"]   = pd.NamedAgg(column="pm10", aggfunc="max")
        # Percentil 95: valor que supera el 95% de las observaciones del día
        # Es más robusto que el máximo porque ignora valores extremos puntuales
        diccionario_agg["pm10_p95"] = pd.NamedAgg(
            column="pm10", aggfunc=lambda x: x.quantile(0.95)
        )
        # Contamos cuántas horas del día tienen dato válido (para evaluar calidad)
        diccionario_agg["horas_validas"] = pd.NamedAgg(column="pm10", aggfunc="count")

    # Para PM2.5: calculamos media y máximo
    if "pm2_5" in df.columns:
        diccionario_agg["pm2_5_media"] = pd.NamedAgg(column="pm2_5", aggfunc="mean")
        diccionario_agg["pm2_5_max"]   = pd.NamedAgg(column="pm2_5", aggfunc="max")

    # Para AOD: calculamos media diaria
    if "aerosol_optical_depth" in df.columns:
        diccionario_agg["aerosol_optical_depth_media"] = pd.NamedAgg(
            column="aerosol_optical_depth", aggfunc="mean"
        )

    # Para AQI europeo: calculamos media y máximo
    if "european_aqi" in df.columns:
        diccionario_agg["european_aqi_media"] = pd.NamedAgg(column="european_aqi", aggfunc="mean")
        diccionario_agg["european_aqi_max"]   = pd.NamedAgg(column="european_aqi", aggfunc="max")

    # Conservamos las coordenadas (tomamos el primer valor del grupo, son iguales en el día)
    if "latitud" in df.columns:
        diccionario_agg["latitud"]  = pd.NamedAgg(column="latitud",  aggfunc="first")
        diccionario_agg["longitud"] = pd.NamedAgg(column="longitud", aggfunc="first")

    # Ejecutamos la agregación: de N filas horarias -> 1 fila diaria por grupo
    df_diario = df.groupby(columnas_grupo).agg(**diccionario_agg).reset_index()

    # Convertimos la fecha de date a datetime para compatibilidad con otras funciones
    df_diario["fecha"] = pd.to_datetime(df_diario["fecha"])

    # ── Paso 4: Clasificación según umbral OMS ────────────────────────────────

    if "pm10_media" in df_diario.columns:
        # Booleano: True si la media diaria de PM10 supera el límite OMS
        df_diario["supera_oms_pm10"] = df_diario["pm10_media"] > PM10_OMS_DIARIO

        # Categoría de nivel de PM10 según rangos
        df_diario["nivel_pm10"] = pd.cut(
            df_diario["pm10_media"],
            bins=[0, PM10_OMS_DIARIO, PM10_ALERTA, float("inf")],   # Límites de categorías
            labels=["normal", "elevado", "alerta"],                   # Nombres de categorías
            include_lowest=True,   # El 0 se incluye en "normal"
        )

        # Registramos cuántos días superaron el límite OMS
        cantidad_superaciones = df_diario["supera_oms_pm10"].sum()
        logger.info(
            f"  Días con PM10 > {PM10_OMS_DIARIO} µg/m³ (límite OMS): {cantidad_superaciones}",
            extra={"etl_stage": "transform", "source": "cams"},
        )

    # Registramos el resultado de la transformación
    logger.info(
        f"Transformación CAMS completa: {cantidad_original} registros horarios "
        f"-> {len(df_diario)} registros diarios",
        extra={"etl_stage": "transform", "source": "cams", "rows_count": len(df_diario)},
    )

    # Guardamos como Parquet si se solicitó
    if guardar and not df_diario.empty:
        nombre_punto = df["punto"].iloc[0].lower() if "punto" in df.columns else "todos"
        ruta_salida = DIR_PROCESADO / f"cams_procesado_{nombre_punto}.parquet"
        ruta_salida.parent.mkdir(parents=True, exist_ok=True)
        df_diario.to_parquet(ruta_salida, index=False)
        logger.info(f"Parquet guardado en: {ruta_salida}")

    return df_diario


# =============================================================================
# BLOQUE DE EJECUCIÓN DIRECTA
# =============================================================================

if __name__ == "__main__":
    import glob

    print("=" * 60)
    print("SINIA-UY — Transformación CAMS (Calidad del Aire)")
    print("=" * 60)

    # Buscamos el CSV más reciente en data/raw/cams/
    archivos = sorted(glob.glob(str(
        Path(__file__).resolve().parent.parent.parent / "data/raw/cams/*.csv"
    )))

    if not archivos:
        print("No hay archivos en data/raw/cams/. Ejecutá primero extract_cams.py")
    else:
        archivo = archivos[-1]   # El más reciente
        print(f"\nProcesando: {Path(archivo).name}\n")

        df_crudo = pd.read_csv(archivo)
        df_diario = transformar_cams(df_crudo)

        print(f"\nRegistros diarios resultantes: {len(df_diario)}")
        columnas_mostrar = [
            c for c in ["fecha", "punto", "pm10_media", "pm10_max",
                         "pm10_p95", "nivel_pm10", "supera_oms_pm10"]
            if c in df_diario.columns
        ]
        print(df_diario[columnas_mostrar].head(15).to_string())
