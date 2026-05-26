from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import psycopg2
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import PG_CONFIG


@st.cache_data(ttl=120)
def query(statement: str, params=()) -> pd.DataFrame:
    with psycopg2.connect(**PG_CONFIG) as conn:
        return pd.read_sql_query(statement, conn, params=params)


st.set_page_config(page_title="Proyecto LIDIA - EC3", layout="wide")
st.title("Proyecto LIDIA | Incendios y condiciones ambientales")
st.caption("Uruguay, Argentina y Brasil | 2018-2025 | Data Warehouse PostgreSQL")

countries = query("SELECT DISTINCT pais_codigo, pais_nombre FROM dw.dim_ubicacion ORDER BY pais_nombre")
selected = st.sidebar.multiselect(
    "Paises", countries["pais_codigo"].tolist(), default=countries["pais_codigo"].tolist()
)
period = st.sidebar.slider("Periodo", 2018, 2025, (2018, 2025))
params = (selected, period[0], period[1])

monthly = query(
    """SELECT * FROM dw.v_incendios_pais_periodo
       WHERE pais_codigo = ANY(%s) AND anio BETWEEN %s AND %s ORDER BY anio, mes, pais_codigo""",
    params,
)
summary = query(
    """SELECT COALESCE(SUM(focos),0)::bigint AS focos, COALESCE(SUM(frp_total_mw),0) AS frp_total,
              COALESCE(AVG(frp_promedio_mw),0) AS frp_promedio,
              COUNT(DISTINCT pais_codigo) AS paises, COUNT(DISTINCT (anio,mes)) AS meses
       FROM dw.v_incendios_pais_periodo
       WHERE pais_codigo = ANY(%s) AND anio BETWEEN %s AND %s""",
    params,
).iloc[0]
quality = query(
    """SELECT COALESCE(SUM(filas_insertadas),0) AS altas, COALESCE(SUM(filas_actualizadas),0) AS modificaciones,
              COALESCE(SUM(filas_rechazadas),0) AS rechazos
       FROM dw.v_calidad_pipeline"""
).iloc[0]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Focos FIRMS", f"{int(summary.focos):,}")
c2.metric("FRP total (MW)", f"{float(summary.frp_total):,.1f}")
c3.metric("FRP promedio (MW)", f"{float(summary.frp_promedio):,.2f}")
c4.metric("Paises con datos", int(summary.paises))
c5, c6, c7, c8 = st.columns(4)
c5.metric("Meses cubiertos", int(summary.meses))
c6.metric("Altas CDC", int(quality.altas))
c7.metric("Modificaciones CDC", int(quality.modificaciones))
c8.metric("Rechazos ETL", int(quality.rechazos))

tab_activity, tab_environment, tab_quality = st.tabs(["Actividad", "Ambiente", "Calidad y CDC"])
with tab_activity:
    st.subheader("Pregunta: como evoluciona la actividad de incendios por mes y pais?")
    if not monthly.empty:
        chart = monthly.assign(periodo=pd.to_datetime(monthly["anio"].astype(str) + "-" + monthly["mes"].astype(str)))
        st.line_chart(chart.pivot_table(index="periodo", columns="pais_nombre", values="focos", aggfunc="sum"))
        st.subheader("Pregunta: que pais presenta mayor FRP total en el periodo?")
        st.bar_chart(monthly.groupby("pais_nombre")["frp_total_mw"].sum())
    region = query(
        "SELECT * FROM dw.v_incendios_region WHERE pais_codigo = ANY(%s) ORDER BY focos DESC LIMIT 15",
        (selected,),
    )
    st.subheader("Pregunta: que regiones concentran mas focos?")
    st.dataframe(region, use_container_width=True, hide_index=True)

with tab_environment:
    climate = query(
        """SELECT * FROM dw.v_incendios_clima
           WHERE pais_codigo = ANY(%s) AND EXTRACT(YEAR FROM fecha) BETWEEN %s AND %s ORDER BY fecha""",
        params,
    )
    rain = query(
        """SELECT * FROM dw.v_incendios_precipitacion
           WHERE pais_codigo = ANY(%s) AND anio BETWEEN %s AND %s ORDER BY anio,mes""",
        params,
    )
    cover = query("SELECT * FROM dw.v_incendios_cobertura WHERE pais_codigo = ANY(%s) ORDER BY focos DESC", (selected,))
    st.subheader("Pregunta: como se relacionan focos, temperatura y humedad?")
    st.dataframe(climate.tail(30), use_container_width=True, hide_index=True)
    st.subheader("Pregunta: cambia la actividad con la precipitacion CHIRPS mensual?")
    st.line_chart(rain.set_index(pd.to_datetime(rain["anio"].astype(str) + "-" + rain["mes"].astype(str)))[["focos", "precipitacion_mm_promedio"]] if not rain.empty else rain)
    st.subheader("Pregunta: que coberturas MODIS se asocian a los focos?")
    st.bar_chart(cover.set_index("cobertura")["focos"] if not cover.empty else cover)

with tab_quality:
    air = query("SELECT * FROM dw.v_calidad_aire_alta_actividad WHERE pais_codigo = ANY(%s) ORDER BY fecha DESC LIMIT 30", (selected,))
    runs = query("SELECT * FROM dw.v_calidad_pipeline LIMIT 30")
    st.info("Calidad del aire se muestra solo si existe una fuente EC3 validada; en su ausencia queda NULL y documentada como pendiente.")
    st.dataframe(air, use_container_width=True, hide_index=True)
    st.subheader("Trazabilidad, tiempos y rechazos del pipeline")
    st.dataframe(runs, use_container_width=True, hide_index=True)
