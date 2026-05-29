"""Extractor opcional para calidad del aire CAMS/Open-Meteo Air Quality."""

from __future__ import annotations

import pandas as pd

from etl.extract.base import read_source


def extract(path=None) -> pd.DataFrame:
    """Lee una fuente validada de PM2.5/PM10 si fue configurada.

    La implementacion no descarga ni fabrica datos: si no hay `CAMS_FILE` o
    `AIR_QUALITY_FILE`, devuelve un lote vacio para dejar la dimension preparada.
    """
    try:
        return read_source("CAMS", path)
    except FileNotFoundError:
        return pd.DataFrame(
            columns=["location", "pais", "lat", "lon", "date", "pm2_5", "pm10"]
        )
