"""
SINIA-UY — Capa analítica de riesgo de incendios
=================================================
Funciones de análisis descriptivo y exploratorio sobre los datos procesados.
Sin Machine Learning predictivo — solo estadística descriptiva y detección
de anomalías con Isolation Forest (análisis exploratorio, no predicción).

Funciones:
    ranking_zonas(df_meteo)              → ranking de puntos por exposición al riesgo
    analisis_estacional(df_meteo)        → patrón mensual del riesgo
    detectar_anomalias(df_meteo)         → días con combinaciones meteorológicas inusuales
    correlacion_focos_riesgo(df_meteo, df_focos) → relación entre índice y focos detectados
"""

from __future__ import annotations

import pandas as pd
import numpy as np


# =============================================================================
# 1. RANKING DE ZONAS POR EXPOSICIÓN AL RIESGO
# =============================================================================

def ranking_zonas(df_meteo: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula un score de riesgo por punto de monitoreo.

    Score = 50% índice de riesgo promedio + 50% proporción de días críticos.
    Ordena de mayor a menor exposición histórica.

    Args:
        df_meteo: DataFrame con columnas punto, indice_riesgo, nivel_riesgo.

    Returns:
        DataFrame con columnas: punto, score_riesgo, indice_promedio,
        dias_criticos, indice_maximo, total_dias.
    """
    if df_meteo.empty or "indice_riesgo" not in df_meteo.columns:
        return pd.DataFrame()

    df = df_meteo.dropna(subset=["indice_riesgo"]).copy()

    ranking = (
        df.groupby("punto")
        .agg(
            indice_promedio=("indice_riesgo", "mean"),
            indice_maximo=("indice_riesgo", "max"),
            dias_criticos=("nivel_riesgo", lambda x: x.isin(["alto", "muy_alto"]).sum()),
            total_dias=("indice_riesgo", "count"),
        )
        .reset_index()
    )

    ranking["score_riesgo"] = (
        ranking["indice_promedio"] * 0.5
        + (ranking["dias_criticos"] / ranking["total_dias"].replace(0, 1)) * 0.5
    ).round(4)

    ranking["indice_promedio"] = ranking["indice_promedio"].round(4)
    ranking["indice_maximo"] = ranking["indice_maximo"].round(4)

    return ranking.sort_values("score_riesgo", ascending=False).reset_index(drop=True)


# =============================================================================
# 2. ANÁLISIS ESTACIONAL
# =============================================================================

def analisis_estacional(df_meteo: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega el índice de riesgo por mes para identificar patrones estacionales.

    Args:
        df_meteo: DataFrame con columnas fecha e indice_riesgo.

    Returns:
        DataFrame con columnas: mes_numero, mes_nombre, riesgo_promedio,
        riesgo_maximo, dias_criticos.
    """
    if df_meteo.empty or "indice_riesgo" not in df_meteo.columns:
        return pd.DataFrame()

    df = df_meteo.copy()
    df["fecha"] = pd.to_datetime(df["fecha"])
    df["mes_numero"] = df["fecha"].dt.month
    df["mes_nombre"] = df["fecha"].dt.strftime("%b")

    estacional = (
        df.groupby(["mes_numero", "mes_nombre"])
        .agg(
            riesgo_promedio=("indice_riesgo", "mean"),
            riesgo_maximo=("indice_riesgo", "max"),
            dias_criticos=(
                "nivel_riesgo",
                lambda x: x.isin(["alto", "muy_alto"]).sum()
            ),
        )
        .reset_index()
        .sort_values("mes_numero")
    )

    estacional["riesgo_promedio"] = estacional["riesgo_promedio"].round(4)
    estacional["riesgo_maximo"] = estacional["riesgo_maximo"].round(4)

    return estacional


# =============================================================================
# 3. DETECCIÓN DE ANOMALÍAS (Isolation Forest)
# =============================================================================

def detectar_anomalias(df_meteo: pd.DataFrame, contaminacion: float = 0.05) -> pd.DataFrame:
    """
    Detecta días con combinaciones meteorológicas inusuales usando Isolation Forest.

    No es predicción — identifica puntos de datos que se alejan del patrón
    habitual (temperatura alta + humedad baja + viento alto simultáneos).

    Args:
        df_meteo:      DataFrame con columnas meteorológicas.
        contaminacion: Proporción esperada de anomalías (default 5%).

    Returns:
        DataFrame original con columna adicional `es_anomalia` (bool)
        y `score_anomalia` (float, menor = más anómalo).
    """
    if df_meteo.empty:
        return df_meteo.copy()

    features = [c for c in [
        "temperature_2m_max",
        "relative_humidity_2m_min",
        "wind_speed_10m_max",
        "et0_fao_evapotranspiration",
        "indice_riesgo",
    ] if c in df_meteo.columns]

    if len(features) < 2:
        df_out = df_meteo.copy()
        df_out["es_anomalia"] = False
        df_out["score_anomalia"] = 0.0
        return df_out

    df_valido = df_meteo.dropna(subset=features).copy()

    if len(df_valido) < 10:
        df_out = df_meteo.copy()
        df_out["es_anomalia"] = False
        df_out["score_anomalia"] = 0.0
        return df_out

    try:
        from sklearn.ensemble import IsolationForest
        from sklearn.preprocessing import StandardScaler

        X = df_valido[features].values
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        modelo = IsolationForest(
            contamination=contaminacion,
            random_state=42,
            n_estimators=100,
        )
        predicciones = modelo.fit_predict(X_scaled)
        scores = modelo.score_samples(X_scaled)

        df_valido = df_valido.copy()
        df_valido["es_anomalia"] = predicciones == -1
        df_valido["score_anomalia"] = scores.round(4)

    except ImportError:
        # Fallback sin sklearn: percentil 95
        p95 = df_valido["indice_riesgo"].quantile(0.95) if "indice_riesgo" in df_valido.columns else 1.0
        df_valido = df_valido.copy()
        df_valido["es_anomalia"] = df_valido.get("indice_riesgo", 0) >= p95
        df_valido["score_anomalia"] = 0.0

    # Merge de vuelta al DataFrame original
    df_out = df_meteo.copy()
    df_out["es_anomalia"] = False
    df_out["score_anomalia"] = 0.0
    df_out.loc[df_valido.index, "es_anomalia"] = df_valido["es_anomalia"].values
    df_out.loc[df_valido.index, "score_anomalia"] = df_valido["score_anomalia"].values

    return df_out


# =============================================================================
# 4. CORRELACIÓN FOCOS - RIESGO
# =============================================================================

def correlacion_focos_riesgo(
    df_meteo: pd.DataFrame,
    df_focos: pd.DataFrame,
) -> dict:
    """
    Calcula la correlación de Pearson entre el índice de riesgo diario
    y la cantidad de focos detectados por día.

    Args:
        df_meteo: DataFrame con columnas fecha e indice_riesgo.
        df_focos: DataFrame con columna fecha_adq (o fecha).

    Returns:
        Dict con: correlacion, n_dias, df_merged (para graficar).
    """
    if df_meteo.empty or df_focos.empty:
        return {"correlacion": None, "n_dias": 0, "df_merged": pd.DataFrame()}

    # Focos por día
    col_fecha = "fecha_adq" if "fecha_adq" in df_focos.columns else "fecha"
    df_f = df_focos.copy()
    df_f[col_fecha] = pd.to_datetime(df_f[col_fecha])
    focos_diario = (
        df_f.set_index(col_fecha)
        .resample("D")
        .size()
        .reset_index()
        .rename(columns={col_fecha: "fecha", 0: "focos"})
    )
    focos_diario["fecha"] = pd.to_datetime(focos_diario["fecha"]).dt.normalize()

    # Riesgo diario promedio (todos los puntos)
    df_m = df_meteo.copy()
    df_m["fecha"] = pd.to_datetime(df_m["fecha"]).dt.normalize()
    riesgo_diario = df_m.groupby("fecha")["indice_riesgo"].mean().reset_index()

    merged = riesgo_diario.merge(focos_diario, on="fecha", how="left").fillna(0)

    if len(merged) < 3:
        return {"correlacion": None, "n_dias": len(merged), "df_merged": merged}

    r = float(merged["indice_riesgo"].corr(merged["focos"]))

    return {
        "correlacion": round(r, 4),
        "n_dias": len(merged),
        "df_merged": merged,
    }
