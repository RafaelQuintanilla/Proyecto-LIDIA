# ETL

El pipeline acepta exclusivamente NASA FIRMS, Open-Meteo historico, CAMS/Open-Meteo
Air Quality, CHIRPS, MODIS e INUMET. En codigo, `METEO` es la etiqueta tecnica
interna de Open-Meteo historico y `CAMS` representa calidad del aire PM2.5/PM10.
FIRMS, CHIRPS, CAMS y una exportacion MODIS pueden configurarse como archivos
reales locales; Open-Meteo historico se obtiene mediante API.
Los datos no se versionan.

```bash
python -m etl.main --source FIRMS
python -m etl.main --source ALL
```

Cada lote valida país, campos críticos, fechas y rangos. Las filas inválidas se
persisten en `staging.rechazos_etl`. `natural_key` identifica la observación y
`record_hash` permite registrar `alta`, `modificacion` o `sin_cambio` en
`audit.cdc_eventos`; la ejecución resume conteos en `audit.etl_runs`.

`INUMET` rechaza registros fuera de Uruguay. `brillo_termico` de FIRMS se
conserva como medición satelital y no se utiliza como temperatura del aire.

## Carga Real Integrada

La carga real integra archivos y APIs disponibles:

```bash
python -m etl.load.real_integrated
```

`FIRMS_FILE` y `CHIRPS_FILE` se configuran con rutas relativas a la raiz del
proyecto. `FIRMS_COUNTRY_BOUNDARIES_FILE` apunta a una geometria auxiliar
local de limites nacionales, utilizada unicamente para asignar
`pais_codigo` a los puntos FIRMS. El cargador acepta solo `URY`, `ARG` y
`BRA`, registra de forma agregada los puntos fuera de alcance y carga
`brightness` como `brillo_termico`.

CHIRPS conserva sus coordenadas de punto para construir
`dw.dim_precipitacion`; la vinculacion a focos usa el punto mas cercano del
mismo pais y mes dentro del umbral configurado. Los registros fuera del alcance
se persisten como rechazos.

`METEO` consume datos historicos horarios 2018-2025 desde Open-Meteo Archive
API. `CAMS`/Open-Meteo Air Quality queda preparado para PM2.5 y PM10; si no hay
archivo validado configurado, el extractor devuelve un lote vacio y no inventa
datos. `MODIS` se carga desde una exportacion anual real configurada en
`MODIS_FILE`. `INUMET` une los CSV horarios reales configurados en
`INUMET_TEMPERATURA_FILE` e `INUMET_HUMEDAD_FILE`, y siempre se restringe a
Uruguay.

Finalizada la ingesta, `associate_environmental_dimensions()` vincula cada
foco FIRMS con el vecino ambiental mas cercano dentro del mismo pais mediante
distancia Haversine. La regla temporal es misma fecha para clima (hora mas
cercana al horario FIRMS), mismo anio/mes para CHIRPS y mismo anio para MODIS.
Los umbrales quedan explicitados en `SPATIAL_THRESHOLDS_KM`: 100 km para
`METEO`, `CHIRPS`, `MODIS` y `CAMS`, y 150 km para `INUMET`. Si no existe
candidato dentro de la regla, la clave foranea permanece nula.
