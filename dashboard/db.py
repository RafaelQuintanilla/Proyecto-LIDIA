"""
SINIA-UY — Capa de acceso a datos del dashboard
================================================
Todas las consultas del dashboard pasan por este módulo.
Estrategia: PostgreSQL primero, fallback a Parquet si la BD no está disponible.
Esto garantiza que el dashboard funcione en desarrollo sin Docker.

Funciones públicas:
    cargar_focos()          → DataFrame de focos históricos
    cargar_meteo()          → DataFrame meteorológico con índice de riesgo
    cargar_cams()           → DataFrame de calidad del aire
    cargar_forecast()       → DataFrame de pronóstico 7 días
    cargar_focos_nrt()      → DataFrame de focos NRT (últimas 24h)
    cargar_resumen_puntos() → DataFrame de último estado por punto
"""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import PG_CONFIG, DIR_PROCESADO

# ─────────────────────────────────────────────────────────────────────────────
# CONEXIÓN
# ─────────────────────────────────────────────────────────────────────────────

def _pg_disponible() -> bool:
    """Verifica si PostgreSQL responde. Falla silenciosamente."""
    try:
        import psycopg2
        conn = psycopg2.connect(**PG_CONFIG, connect_timeout=3)
        conn.close()
        return True
    except Exception:
        return False


def _query_pg(sql: str, params: tuple = ()) -> pd.DataFrame:
    """Ejecuta una query en PostgreSQL y devuelve un DataFrame."""
    import psycopg2
    conn = psycopg2.connect(**PG_CONFIG, connect_timeout=5)
    try:
        df = pd.read_sql_query(sql, conn, params=params)
        return df
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# FOCOS DE CALOR — HISTÓRICO
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def cargar_focos(fecha_inicio: str | None = None, fecha_fin: str | None = None, pais: str | None = None) -> pd.DataFrame:
    """
    Focos de calor históricos filtrados por fecha y/o país.
    Devuelve hasta 100 000 focos ordenados por FRP descendente (los más intensos primero).
    Fuente: tabla focos_calor (PostgreSQL) o firms_procesado.parquet (fallback).
    """
    if _pg_disponible():
        try:
            where_clauses = []
            params: list = []
            if fecha_inicio:
                where_clauses.append("fecha_adq >= %s")
                params.append(fecha_inicio)
            if fecha_fin:
                where_clauses.append("fecha_adq <= %s")
                params.append(fecha_fin)
            if pais:
                where_clauses.append("pais = %s")
                params.append(pais)
            where = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

            df = _query_pg(f"""
                SELECT
                    fecha_adq,
                    latitud,
                    longitud,
                    potencia_radiativa,
                    confianza_raw,
                    confianza_num,
                    satelite,
                    dia_noche,
                    es_diurno,
                    pais
                FROM focos_calor
                {where}
                ORDER BY potencia_radiativa DESC NULLS LAST
                LIMIT 100000
            """, tuple(params))
            df["fecha_adq"] = pd.to_datetime(df["fecha_adq"])
            df.attrs["fuente"] = "postgresql"
            return df
        except Exception as e:
            st.sidebar.warning(f"BD no disponible, usando parquet: {e}")

    # Fallback: parquet
    p = DIR_PROCESADO / "firms_procesado.parquet"
    if p.exists():
        df = pd.read_parquet(p)
        df["fecha_adq"] = pd.to_datetime(df["fecha_adq"])
        df.attrs["fuente"] = "parquet"
        return df
    return pd.DataFrame()


# ─────────────────────────────────────────────────────────────────────────────
# FOCOS NRT
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=180)
def cargar_focos_nrt() -> pd.DataFrame:
    """Focos NRT de las últimas 24h. Solo parquet (datos muy recientes)."""
    p = DIR_PROCESADO / "firms_nrt_procesado.parquet"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_parquet(p)
    df["fecha_adq"] = pd.to_datetime(df["fecha_adq"])
    return df


# ─────────────────────────────────────────────────────────────────────────────
# METEOROLOGÍA + ÍNDICE DE RIESGO
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def cargar_meteo(tipo_dato: str = "historico") -> pd.DataFrame:
    """
    Datos meteorológicos con índice de riesgo.
    Fuente: vista v_riesgo_historico (PostgreSQL) o parquet (fallback).
    """
    if _pg_disponible():
        try:
            df = _query_pg("""
                SELECT
                    punto,
                    fecha,
                    tipo_dato,
                    indice_riesgo,
                    nivel_riesgo,
                    temperature_2m_max,
                    temperature_2m_min,
                    relative_humidity_2m_min,
                    wind_speed_10m_max,
                    precipitation_sum,
                    et0_fao_evapotranspiration
                FROM v_riesgo_historico
                WHERE tipo_dato = %s
                ORDER BY punto, fecha
            """, (tipo_dato,))
            df["fecha"] = pd.to_datetime(df["fecha"])
            df.attrs["fuente"] = "postgresql"
            return df
        except Exception as e:
            st.sidebar.warning(f"BD no disponible, usando parquet: {e}")

    # Fallback: parquet
    frames = [pd.read_parquet(f) for f in DIR_PROCESADO.glob("meteo_procesado_*.parquet")]
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    df["fecha"] = pd.to_datetime(df["fecha"])
    df.attrs["fuente"] = "parquet"
    return df


# ─────────────────────────────────────────────────────────────────────────────
# FORECAST
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def cargar_forecast() -> pd.DataFrame:
    """
    Pronóstico de riesgo 7 días.
    Fuente: vista v_forecast_riesgo (PostgreSQL) o parquet (fallback).
    """
    if _pg_disponible():
        try:
            df = _query_pg("""
                SELECT
                    punto,
                    fecha,
                    indice_riesgo,
                    nivel_riesgo,
                    temperature_2m_max,
                    relative_humidity_2m_min,
                    wind_speed_10m_max,
                    precipitation_probability_max
                FROM v_forecast_riesgo
                ORDER BY punto, fecha
            """)
            df["fecha"] = pd.to_datetime(df["fecha"])
            df.attrs["fuente"] = "postgresql"
            return df
        except Exception as e:
            st.sidebar.warning(f"BD no disponible, usando parquet: {e}")

    p = DIR_PROCESADO / "forecast_riesgo.parquet"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_parquet(p)
    df["fecha"] = pd.to_datetime(df["fecha"])
    df.attrs["fuente"] = "parquet"
    return df


# ─────────────────────────────────────────────────────────────────────────────
# CALIDAD DEL AIRE
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def cargar_cams() -> pd.DataFrame:
    """
    Datos diarios de calidad del aire.
    Fuente: tabla calidad_aire_diario (PostgreSQL) o parquet (fallback).
    """
    if _pg_disponible():
        try:
            df = _query_pg("""
                SELECT
                    p.nombre AS punto,
                    c.fecha,
                    c.pm10_media,
                    c.pm10_max,
                    c.pm10_p95,
                    c.pm2_5_media,
                    c.european_aqi_media,
                    c.supera_oms_pm10,
                    c.nivel_pm10,
                    c.horas_validas
                FROM calidad_aire_diario c
                JOIN puntos_monitoreo p ON p.id = c.id_punto
                ORDER BY c.fecha DESC
            """)
            df["fecha"] = pd.to_datetime(df["fecha"])
            df.attrs["fuente"] = "postgresql"
            return df
        except Exception as e:
            st.sidebar.warning(f"BD no disponible, usando parquet: {e}")

    frames = [pd.read_parquet(f) for f in DIR_PROCESADO.glob("cams_*.parquet")]
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    df["fecha"] = pd.to_datetime(df["fecha"])
    df.attrs["fuente"] = "parquet"
    return df


# ─────────────────────────────────────────────────────────────────────────────
# RESUMEN EJECUTIVO POR PUNTO (para KPIs del dashboard)
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def cargar_resumen_puntos() -> pd.DataFrame:
    """
    Último estado de cada punto de monitoreo.
    Fuente: vista v_riesgo_actual (PostgreSQL) — sin fallback (es analítica pura).
    """
    if _pg_disponible():
        try:
            return _query_pg("SELECT * FROM v_riesgo_actual ORDER BY indice_riesgo DESC NULLS LAST")
        except Exception:
            pass
    return pd.DataFrame()


# ─────────────────────────────────────────────────────────────────────────────
# DÍAS CRÍTICOS
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=600)
def cargar_dias_criticos() -> pd.DataFrame:
    """Días históricos con riesgo ALTO o MUY ALTO en al menos un punto."""
    if _pg_disponible():
        try:
            return _query_pg("SELECT * FROM v_dias_criticos ORDER BY fecha DESC")
        except Exception:
            pass
    return pd.DataFrame()


# ─────────────────────────────────────────────────────────────────────────────
# MÉTRICAS DE RENDIMIENTO (para defensa)
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=600)
def cargar_riesgo_por_pais() -> pd.DataFrame:
    """Riesgo mensual agregado por país — usa vista v_riesgo_por_pais."""
    if _pg_disponible():
        try:
            df = _query_pg("SELECT * FROM v_riesgo_por_pais ORDER BY pais, mes")
            df["mes"] = pd.to_datetime(df["mes"])
            df.attrs["fuente"] = "postgresql"
            return df
        except Exception:
            pass
    return pd.DataFrame()


@st.cache_data(ttl=600)
def cargar_focos_por_pais_mes() -> pd.DataFrame:
    """Focos de calor mensuales por país — usa vista v_focos_por_pais_mes."""
    if _pg_disponible():
        try:
            df = _query_pg("SELECT * FROM v_focos_por_pais_mes ORDER BY pais, mes")
            df["mes"] = pd.to_datetime(df["mes"])
            df.attrs["fuente"] = "postgresql"
            return df
        except Exception:
            pass
    return pd.DataFrame()


def medir_tiempos_consultas() -> dict[str, float]:
    """
    Mide el tiempo de ejecución de consultas representativas.
    Retorna dict con tiempos en segundos.
    Usar en la sección de métricas del informe final.
    """
    import time
    if not _pg_disponible():
        return {}

    resultados = {}
    consultas = {
        "focos_por_mes":       "SELECT DATE_TRUNC('month', fecha_adq), COUNT(*) FROM focos_calor GROUP BY 1",
        "riesgo_promedio_punto": "SELECT punto, AVG(indice_riesgo) FROM v_riesgo_historico GROUP BY punto",
        "alertas_calidad_aire": "SELECT * FROM v_alertas_calidad_aire LIMIT 100",
        "dias_criticos":        "SELECT * FROM v_dias_criticos",
    }
    for nombre, sql in consultas.items():
        t0 = time.perf_counter()
        try:
            _query_pg(sql)
            resultados[nombre] = round(time.perf_counter() - t0, 4)
        except Exception as e:
            resultados[nombre] = f"error: {e}"

    return resultados
