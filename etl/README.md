# ETL

El pipeline acepta exclusivamente `INUMET`, `FIRMS`, `CHIRPS`, `FORECAST`,
`METEO` y `MODIS`. Las rutas de CSV o Parquet se configuran en
`config/.env`; los datos no se versionan.

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

## Carga Real Controlada FIRMS/CHIRPS

La carga inicial con volumen real se ejecuta solamente para fuentes con
archivos disponibles:

```bash
python -m etl.load.real_firms_chirps --source BOTH
```

`FIRMS_FILE` y `CHIRPS_FILE` se configuran con rutas relativas a la raiz del
proyecto. `FIRMS_COUNTRY_BOUNDARIES_FILE` apunta a una geometria auxiliar
local de limites nacionales, utilizada unicamente para asignar
`pais_codigo` a los puntos FIRMS. El cargador acepta solo `URY`, `ARG` y
`BRA`, registra de forma agregada los puntos fuera de alcance y carga
`brightness` como `brillo_termico`.

CHIRPS conserva sus coordenadas de punto para construir
`dw.dim_precipitacion`; la vista analitica compara precipitacion y focos a
nivel pais-mes, sin forzar coincidencias puntuales inexistentes. Los registros
fuera del alcance se persisten como rechazos. `METEO`, `FORECAST`, `MODIS` e
`INUMET` quedan pendientes mientras no exista un archivo real configurado.
