# =============================================================================
# SINIA-UY — Transformación Meteorológica e Índice de Riesgo
# =============================================================================
# Este módulo es el núcleo analítico del proyecto.
# Toma los datos meteorológicos crudos y calcula el ÍNDICE DE RIESGO DE INCENDIO
# para cada día y cada punto de monitoreo.
#
# El índice de riesgo es un número entre 0 (sin riesgo) y 1 (riesgo máximo)
# calculado como suma ponderada de 4 componentes:
#
#   Índice = (temp × 0.25) + (humedad × 0.30) + (viento × 0.20) + (sequía × 0.25)
#
# Cada componente se normaliza al rango [0,1] usando umbrales de referencia
# basados en condiciones extremas observadas históricamente en Uruguay.
#
# Niveles de riesgo:
#   0.00 - 0.25 -> BAJO      (verde)
#   0.25 - 0.50 -> MODERADO  (amarillo)
#   0.50 - 0.75 -> ALTO      (naranja)
#   0.75 - 1.00 -> MUY ALTO  (rojo)
# =============================================================================

from pathlib import Path

import pandas as pd   # Para transformación de datos
import numpy as np    # Para operaciones matemáticas (normalización, NaN)

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from config.settings import DIR_PROCESADO, PESOS_RIESGO
from etl.utils.logger import setup_logger

logger = setup_logger("sinia.transform.meteo")

# -----------------------------------------------------------------------------
# UMBRALES DE NORMALIZACIÓN
# Estos valores definen el rango "sin riesgo" a "riesgo máximo" para cada variable.
# Basados en climatología histórica de Uruguay y literatura sobre incendios forestales.
# -----------------------------------------------------------------------------

TEMP_MAX_REF   = 42.0   # °C — temperatura de referencia máxima (riesgo extremo)
TEMP_MIN_REF   = 15.0   # °C — por debajo de esto el calor no contribuye al riesgo
HUM_MIN_REF    = 10.0   # % — humedad mínima crítica (combustible completamente seco)
HUM_MAX_REF    = 80.0   # % — por encima de esto la humedad no reduce el riesgo
VIENTO_MAX_REF = 80.0   # km/h — viento máximo de referencia para propagación extrema
ET0_MAX_REF    = 8.0    # mm/día — evapotranspiración máxima (sequía extrema)


# =============================================================================
# FUNCIÓN AUXILIAR: Normalización
# =============================================================================

def _normalizar(
    serie: pd.Series,    # Serie de pandas con los valores a normalizar
    min_val: float,      # Valor mínimo de la escala (corresponde a riesgo=0)
    max_val: float,      # Valor máximo de la escala (corresponde a riesgo=1)
    invertir: bool = False,  # Si True, valores menores dan mayor riesgo (ej: humedad)
) -> pd.Series:
    """
    Normaliza una serie de valores al rango [0, 1].

    Para temperatura y viento: más alto = más riesgo (invertir=False)
    Para humedad: más bajo = más riesgo (invertir=True)

    Ejemplo para temperatura (min=15°C, max=42°C, no invertir):
        15°C -> 0.0 (sin riesgo)
        28°C -> 0.48 (riesgo moderado)
        42°C -> 1.0 (riesgo máximo)

    Ejemplo para humedad (min=10%, max=80%, invertir=True):
        80% -> 0.0 (sin riesgo, mucha humedad)
        45% -> 0.5 (riesgo moderado)
        10% -> 1.0 (riesgo máximo, muy seco)
    """
    # Aplicamos la fórmula de normalización lineal: (valor - min) / (max - min)
    normalizado = (serie - min_val) / (max_val - min_val)

    # Recortamos al rango [0, 1] — valores fuera del rango se llevan al límite
    normalizado = normalizado.clip(0, 1)

    # Si hay que invertir (más bajo = más riesgo), devolvemos 1 - normalizado
    return (1 - normalizado) if invertir else normalizado


# =============================================================================
# FUNCIÓN PRINCIPAL DE TRANSFORMACIÓN
# =============================================================================

def transformar_meteo(df: pd.DataFrame, guardar: bool = True) -> pd.DataFrame:
    """
    Transforma datos meteorológicos crudos y calcula el índice de riesgo de incendio.

    Pasos de transformación:
    1. Casteo de tipos (strings -> datetime, strings -> float)
    2. Detección y reporte de valores nulos en campos críticos
    3. Normalización de cada componente de riesgo al rango [0,1]
    4. Cálculo del índice de riesgo ponderado
    5. Clasificación del nivel de riesgo (bajo/moderado/alto/muy_alto)

    Args:
        df:       DataFrame crudo de Open-Meteo (granularidad daily)
        guardar:  Si True, guarda el resultado como Parquet en data/processed/

    Returns:
        DataFrame enriquecido con columnas adicionales:
        - riesgo_temp:    componente temperatura normalizada [0,1]
        - riesgo_humedad: componente humedad normalizada [0,1]
        - riesgo_viento:  componente viento normalizada [0,1]
        - riesgo_sequia:  componente sequía normalizada [0,1]
        - indice_riesgo:  índice ponderado final [0,1]
        - nivel_riesgo:   categoría (bajo/moderado/alto/muy_alto)
    """
    if df.empty:
        logger.warning("transformar_meteo: DataFrame vacío, sin datos para transformar")
        return df

    cantidad_original = len(df)

    logger.info(
        f"Iniciando transformación meteorológica: {cantidad_original} registros",
        extra={"etl_stage": "transform", "source": "meteo"},
    )

    # Hacemos una copia para no modificar el DataFrame original
    df = df.copy()

    # ── Paso 1: Casteo de tipos ───────────────────────────────────────────────

    # Convertimos la columna de fecha según la granularidad
    if "fecha" in df.columns:
        # Datos diarios: la columna se llama "fecha" (ej: "2024-01-15")
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    elif "fecha_hora" in df.columns:
        # Datos horarios: la columna se llama "fecha_hora" (ej: "2024-01-15T14:00")
        df["fecha_hora"] = pd.to_datetime(df["fecha_hora"], errors="coerce")

    # Convertimos todas las columnas de texto que deberían ser numéricas
    # Excluimos columnas que legítimamente son texto
    for columna in df.select_dtypes(include=["object"]).columns:
        if columna not in ["punto", "fecha", "fecha_hora"]:
            df[columna] = pd.to_numeric(df[columna], errors="coerce")

    # ── Paso 2: Detección de nulos en campos críticos ────────────────────────

    # Campos que DEBEN tener datos para calcular el índice de riesgo
    campos_criticos = [
        "temperature_2m_max",           # Temperatura máxima diaria
        "relative_humidity_2m_min",     # Humedad mínima diaria
        "wind_speed_10m_max",           # Viento máximo diario
        "et0_fao_evapotranspiration",   # Evapotranspiración (proxy de sequía)
    ]

    for campo in campos_criticos:
        if campo in df.columns:
            cantidad_nulos = df[campo].isna().sum()   # Contamos los valores nulos
            if cantidad_nulos > 0:
                # Registramos el aviso pero continuamos — el índice maneja nulos
                logger.warning(
                    f"  Campo {campo}: {cantidad_nulos} valores nulos "
                    f"({cantidad_nulos / len(df) * 100:.1f}%)",
                    extra={"etl_stage": "transform", "source": "meteo"},
                )

    # ── Paso 3: Cálculo de componentes de riesgo normalizadas ────────────────
    # Solo calculamos si tenemos datos diarios (temperatura máxima presente)

    if "temperature_2m_max" in df.columns:

        # Componente TEMPERATURA: más calor -> más riesgo
        # Min 15°C (sin riesgo) -> Max 42°C (riesgo máximo)
        df["riesgo_temp"] = _normalizar(
            df["temperature_2m_max"],
            min_val=TEMP_MIN_REF,
            max_val=TEMP_MAX_REF,
            invertir=False,   # Mayor temperatura = mayor riesgo
        )

        # Componente HUMEDAD: menos humedad -> más riesgo (vegetación seca)
        # Max 80% (sin riesgo, vegetación húmeda) -> Min 10% (riesgo máximo, vegetación seca)
        if "relative_humidity_2m_min" in df.columns:
            df["riesgo_humedad"] = _normalizar(
                df["relative_humidity_2m_min"],
                min_val=HUM_MIN_REF,
                max_val=HUM_MAX_REF,
                invertir=True,   # Menor humedad = mayor riesgo
            )
        else:
            df["riesgo_humedad"] = np.nan   # NaN si no hay datos de humedad

        # Componente VIENTO: más viento -> más riesgo (propaga el fuego)
        # Min 0 km/h (sin riesgo) -> Max 80 km/h (riesgo máximo)
        if "wind_speed_10m_max" in df.columns:
            df["riesgo_viento"] = _normalizar(
                df["wind_speed_10m_max"],
                min_val=0,
                max_val=VIENTO_MAX_REF,
                invertir=False,   # Mayor viento = mayor riesgo
            )
        else:
            df["riesgo_viento"] = np.nan

        # Componente SEQUÍA: mayor evapotranspiración -> más sequía -> más riesgo
        # La ET0 es un indicador del estrés hídrico de la vegetación
        # Min 0 mm/día -> Max 8 mm/día (sequía extrema)
        if "et0_fao_evapotranspiration" in df.columns:
            df["riesgo_sequia"] = _normalizar(
                df["et0_fao_evapotranspiration"],
                min_val=0,
                max_val=ET0_MAX_REF,
                invertir=False,   # Mayor ET0 = mayor riesgo de sequía
            )
        else:
            df["riesgo_sequia"] = np.nan

        # ── Paso 4: Cálculo del índice de riesgo ponderado ───────────────────
        # El índice es la suma de cada componente multiplicada por su peso
        # Si una componente tiene NaN, redistribuimos su peso entre las demás

        # Mapeamos cada factor de riesgo a su columna correspondiente
        componentes = {
            "temperatura": "riesgo_temp",     # Peso 0.25
            "humedad":     "riesgo_humedad",  # Peso 0.30
            "viento":      "riesgo_viento",   # Peso 0.20
            "sequia":      "riesgo_sequia",   # Peso 0.25
        }

        # Inicializamos el índice y el peso total acumulado en 0 para cada fila
        indice_acumulado = pd.Series(0.0, index=df.index)
        peso_total_valido = pd.Series(0.0, index=df.index)

        for factor, columna in componentes.items():
            peso = PESOS_RIESGO[factor]       # Obtenemos el peso de la configuración
            tiene_dato = df[columna].notna()   # True donde hay dato, False donde hay NaN

            # Sumamos la contribución ponderada de este factor
            # fillna(0) reemplaza NaN por 0 para la suma (su peso no se cuenta)
            indice_acumulado += df[columna].fillna(0) * peso

            # Acumulamos el peso solo de los factores con datos válidos
            peso_total_valido += tiene_dato * peso

        # Evitamos división por cero (si todos los factores son NaN)
        peso_total_valido = peso_total_valido.replace(0, np.nan)

        # El índice final se renormaliza por el peso válido acumulado
        # Esto redistribuye el peso de los factores NaN entre los que tienen datos
        df["indice_riesgo"] = (indice_acumulado / peso_total_valido).round(4)

        # ── Paso 5: Clasificación del nivel de riesgo ─────────────────────────
        # Cortamos el índice en 4 categorías usando pd.cut()
        df["nivel_riesgo"] = pd.cut(
            df["indice_riesgo"],
            bins=[0, 0.25, 0.50, 0.75, 1.01],   # Límites de cada categoría
            labels=["bajo", "moderado", "alto", "muy_alto"],   # Nombre de cada categoría
            include_lowest=True,   # El límite inferior (0) se incluye en el primer bin
        )

        # Registramos la distribución de niveles de riesgo en el log
        logger.info(
            "Índice de riesgo calculado. Distribución de niveles:\n"
            + df["nivel_riesgo"].value_counts().to_string(),
            extra={"etl_stage": "transform", "source": "meteo"},
        )

    # Registramos el resultado final
    logger.info(
        f"Transformación meteorológica completa: {len(df)} registros procesados",
        extra={"etl_stage": "transform", "source": "meteo", "rows_count": len(df)},
    )

    # Guardamos como Parquet si se solicitó
    if guardar and not df.empty:
        # El nombre incluye el punto para diferenciar archivos por departamento
        nombre_punto = df["punto"].iloc[0].lower() if "punto" in df.columns else "todos"
        ruta_salida = DIR_PROCESADO / f"meteo_procesado_{nombre_punto}.parquet"
        ruta_salida.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(ruta_salida, index=False)
        logger.info(f"Parquet guardado en: {ruta_salida}")

    return df


# =============================================================================
# FUNCIÓN: Procesar todos los archivos meteorológicos disponibles
# =============================================================================

def transformar_meteo_todos(guardar: bool = True) -> pd.DataFrame:
    """
    Procesa todos los CSVs meteorológicos diarios en data/raw/meteo/.

    Útil para reprocesar todos los datos históricos de una vez.

    Returns:
        DataFrame consolidado con índice de riesgo para todos los puntos y fechas.
    """
    import glob

    # Buscamos todos los CSVs de granularidad diaria en la carpeta de datos crudos
    patron = str(
        Path(__file__).resolve().parent.parent.parent
        / "data/raw/meteo/*_daily_*.csv"
    )
    archivos = glob.glob(patron)   # Lista de archivos que coinciden con el patrón

    if not archivos:
        logger.warning("No hay archivos meteorológicos diarios en data/raw/meteo/")
        return pd.DataFrame()

    # Procesamos cada archivo y acumulamos en la lista
    frames = []
    for archivo in sorted(archivos):   # sorted() para procesar en orden cronológico
        df_crudo = pd.read_csv(archivo)
        df_procesado = transformar_meteo(df_crudo, guardar=False)   # No guardamos individuales
        frames.append(df_procesado)

    # Concatenamos todos en un único DataFrame
    resultado = pd.concat(frames, ignore_index=True)

    if guardar:
        ruta_salida = DIR_PROCESADO / "meteo_procesado_todos.parquet"
        ruta_salida.parent.mkdir(parents=True, exist_ok=True)
        resultado.to_parquet(ruta_salida, index=False)
        logger.info(f"Parquet consolidado guardado en: {ruta_salida}")

    return resultado


# =============================================================================
# BLOQUE DE EJECUCIÓN DIRECTA
# =============================================================================

if __name__ == "__main__":
    import json

    print("=" * 60)
    print("SINIA-UY — Transformación Meteorológica + Índice de Riesgo")
    print("=" * 60)

    # Leemos el CSV de Rivera ya descargado previamente
    ruta_csv = (
        Path(__file__).resolve().parent.parent.parent
        / "data/raw/meteo/meteo_rivera_daily_2024-01-01_2024-03-31.csv"
    )

    df_crudo = pd.read_csv(ruta_csv)
    df_procesado = transformar_meteo(df_crudo)

    # Columnas relevantes para mostrar el resultado del índice de riesgo
    columnas_resultado = [
        "fecha", "punto", "temperature_2m_max", "relative_humidity_2m_min",
        "wind_speed_10m_max", "riesgo_temp", "riesgo_humedad",
        "riesgo_viento", "riesgo_sequia", "indice_riesgo", "nivel_riesgo"
    ]
    columnas_presentes = [c for c in columnas_resultado if c in df_procesado.columns]

    print(f"\nRegistros procesados: {len(df_procesado)}")
    print(f"\nResultado con índice de riesgo:")
    print(df_procesado[columnas_presentes].head(10).to_string())
    print(f"\nDistribución de niveles de riesgo:")
    print(df_procesado["nivel_riesgo"].value_counts())
