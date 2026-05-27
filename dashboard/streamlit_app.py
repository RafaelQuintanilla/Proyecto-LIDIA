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
    with psycopg2.connect(**PG_CONFIG) as connection:
        with connection.cursor() as cursor:
            cursor.execute(statement, params)
            columns = [column.name for column in cursor.description]
            return pd.DataFrame(cursor.fetchall(), columns=columns)


st.set_page_config(page_title="Proyecto LIDIA - EC3", layout="wide")
st.title("Proyecto LIDIA | Incendios y variables ambientales")
st.caption("Uruguay, Argentina y Brasil | 2018-2025 | Data Warehouse PostgreSQL")

countries = pd.DataFrame(
    [("URY", "Uruguay"), ("ARG", "Argentina"), ("BRA", "Brasil")],
    columns=["pais_codigo", "pais_nombre"],
)
selected = st.sidebar.multiselect(
    "Paises", countries["pais_codigo"].tolist(), default=countries["pais_codigo"].tolist()
)
period = st.sidebar.slider("Periodo", 2018, 2025, (2018, 2025))
params = (selected, period[0], period[1])

monthly = query(
    """SELECT pais_codigo, pais_nombre, anio, mes, focos, frp_promedio_mw, frp_total_mw
       FROM dw.v_incendios_pais_periodo
       WHERE pais_codigo = ANY(%s) AND anio BETWEEN %s AND %s
       ORDER BY anio, mes, pais_codigo""",
    params,
)
focos = int(monthly["focos"].sum()) if not monthly.empty else 0
frp_total = float(monthly["frp_total_mw"].sum()) if not monthly.empty else 0.0
frp_promedio = frp_total / focos if focos else 0.0
paises = int(monthly["pais_codigo"].nunique()) if not monthly.empty else 0
meses = int(monthly[["anio", "mes"]].drop_duplicates().shape[0]) if not monthly.empty else 0
quality = query(
    """SELECT COALESCE(SUM(filas_insertadas), 0)::bigint AS altas,
              COALESCE(SUM(filas_actualizadas), 0)::bigint AS modificaciones,
              COALESCE(SUM(filas_rechazadas), 0)::bigint AS rechazos
       FROM dw.v_calidad_pipeline"""
).iloc[0]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Focos FIRMS", f"{focos:,}")
c2.metric("FRP total (MW)", f"{frp_total:,.1f}")
c3.metric("FRP promedio (MW)", f"{frp_promedio:,.2f}")
c4.metric("Paises con datos", paises)
c5, c6, c7, c8 = st.columns(4)
c5.metric("Meses cubiertos", meses)
c6.metric("Altas CDC", f"{int(quality.altas):,}")
c7.metric("Modificaciones CDC", f"{int(quality.modificaciones):,}")
c8.metric("Rechazos ETL", f"{int(quality.rechazos):,}")

section = st.radio("Analisis", ["Actividad", "Ambiente", "Calidad y CDC"], horizontal=True)
if section == "Actividad":
    st.subheader("Evolucion mensual de focos por pais")
    if not monthly.empty:
        chart = monthly.assign(
            periodo=pd.to_datetime(dict(year=monthly["anio"], month=monthly["mes"], day=1))
        )
        st.line_chart(chart.pivot_table(index="periodo", columns="pais_nombre", values="focos"))
        st.subheader("FRP total por pais en el periodo")
        st.bar_chart(monthly.groupby("pais_nombre")["frp_total_mw"].sum())
    region = query(
        """SELECT pais_codigo, region, focos, frp_promedio_mw
           FROM dw.v_incendios_region
           WHERE pais_codigo = ANY(%s)
           ORDER BY focos DESC LIMIT 15""",
        (selected,),
    )
    st.subheader("Regiones con mayor actividad")
    st.dataframe(region, width="stretch", hide_index=True)

elif section == "Ambiente":
    climate = query(
        """SELECT pais_codigo, fecha, focos, frp_promedio_mw, temperatura_media_c, humedad_media_pct
           FROM dw.v_incendios_clima
           WHERE pais_codigo = ANY(%s) AND EXTRACT(YEAR FROM fecha) BETWEEN %s AND %s
           ORDER BY fecha DESC LIMIT 90""",
        params,
    )
    rain = query(
        """SELECT pais_codigo, anio, mes, focos, precipitacion_mm_promedio
           FROM dw.v_incendios_precipitacion
           WHERE pais_codigo = ANY(%s) AND anio BETWEEN %s AND %s
           ORDER BY anio, mes""",
        params,
    )
    cover = query(
        """SELECT pais_codigo, cobertura, focos, frp_promedio_mw
           FROM dw.v_incendios_cobertura
           WHERE pais_codigo = ANY(%s) ORDER BY focos DESC""",
        (selected,),
    )
    st.subheader("Focos, temperatura y humedad")
    st.dataframe(climate, width="stretch", hide_index=True)
    st.subheader("Actividad y precipitacion mensual CHIRPS")
    if not rain.empty:
        rain = rain.assign(periodo=pd.to_datetime(dict(year=rain["anio"], month=rain["mes"], day=1)))
        st.line_chart(rain.set_index("periodo")[["focos", "precipitacion_mm_promedio"]])
    st.subheader("Focos por cobertura vegetal MODIS")
    st.bar_chart(cover.set_index("cobertura")["focos"] if not cover.empty else cover)

else:
    air = query(
        """SELECT pais_codigo, fecha, focos, pm25, pm10, estado_dato
           FROM dw.v_calidad_aire_alta_actividad
           WHERE pais_codigo = ANY(%s) ORDER BY fecha DESC LIMIT 30""",
        (selected,),
    )
    runs = query(
        """SELECT fuente, estado, iniciado_en, finalizado_en, duracion_segundos,
                  filas_leidas, filas_insertadas, filas_actualizadas, filas_rechazadas
           FROM dw.v_calidad_pipeline LIMIT 30"""
    )
    st.info("Calidad del aire queda nula o pendiente cuando no existe un dato EC3 validado.")
    st.dataframe(air, width="stretch", hide_index=True)
    st.subheader("Trazabilidad del pipeline")
    st.dataframe(runs, width="stretch", hide_index=True)
