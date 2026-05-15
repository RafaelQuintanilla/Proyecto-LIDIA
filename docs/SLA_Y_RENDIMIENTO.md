# SLA y rendimiento

Fecha de medicion: 2026-05-15.

Evidencia generada por:

```bash
python scripts/medir_rendimiento.py
```

Reportes:

- `reports/rendimiento_ultimo.json`
- `reports/rendimiento_20260515_101445.json`

## SLA definidos

| Dimension | SLA esperado | Justificacion | Resultado medido | Estado |
|---|---:|---|---:|---|
| Carga completa local desde datos procesados | <= 15 min | Volumen academico, reprocesable y no transaccional | Lectura total de FIRMS: 750.991 ms; datasets menores: < 14 ms cada uno | Cumple para lectura procesada |
| Carga incremental NRT | <= 2 min | El dashboard debe poder refrescar datos recientes sin reprocesar todo | Simulacion ultimos 7 dias FIRMS: 148.510 ms promedio | Cumple |
| Consulta analitica representativa | <= 3000 ms | Uso interactivo en Streamlit | Peor consulta medida: focos por mes, 490.622 ms promedio | Cumple |
| Consulta de calidad/riesgo por punto | <= 1000 ms | KPI operativo de dashboard | Riesgo por punto: 3.533 ms; PM10 por punto: 4.515 ms | Cumple |
| Frecuencia minima de actualizacion | Historico diario; NRT cada 1-3 h | FIRMS NRT y CAMS tienen valor operativo si se actualizan varias veces al dia | `etl/scheduler.py` define jobs NRT/forecast/CAMS | Cumple en diseno operativo |

## Metricas medidas

| Medicion | Filas / resultado | Tiempo promedio |
|---|---:|---:|
| Lectura `firms_procesado.parquet` | 1.836.537 filas | 750.991 ms |
| Lectura `meteo_procesado_todos.parquet` | 23.104 filas | 13.945 ms |
| Lectura `cams_procesado_todos.parquet` | 23.199 filas | 9.171 ms |
| Q1 focos por mes | 12 meses | 490.622 ms |
| Q2 ranking dias con mas focos | top 15, 417.340 focos acumulados | 54.646 ms |
| Q3 dias de riesgo alto/muy alto por punto | 5.748 dias criticos | 3.533 ms |
| Q4 PM10 promedio por punto | max promedio 21.7415 | 4.515 ms |
| Incremental FIRMS ultimos 7 dias | 12.145 registros | 148.510 ms |
| Carga doble idempotente simulada | 100.000 registros finales | 87.158 ms |

## Interpretacion tecnica

El resultado mas costoso es la agregacion temporal sobre FIRMS completo, que promedia
490.622 ms sobre 1.836.537 registros. Esta medicion esta por debajo del SLA interactivo
de 3000 ms. En la arquitectura con PostgreSQL, los indices definidos en
`sql/ddl/03_indices.sql` apuntan a los mismos patrones de consulta: fecha, punto,
nivel de riesgo y combinaciones temporales.

El incremental de ultimos 7 dias procesa 12.145 registros en 148.510 ms promedio. Esto
respalda la decision de usar watermark CDC en `etl/scheduler.py`: el pipeline no necesita
leer toda la historia para refrescar el tablero operativo.

La prueba de idempotencia simulada duplica 100.000 registros y deduplica por clave natural,
quedando nuevamente en 100.000 registros. Esto es coherente con los tests formales de
`tests/test_calidad_datos.py`, que el 2026-05-15 dieron 17 PASS / 0 FAIL.

## Comparacion antes/despues e indices

En el repositorio los indices analiticos ya estan definidos en `sql/ddl/03_indices.sql`.
Para una defensa final con PostgreSQL activo, ejecutar:

```sql
EXPLAIN ANALYZE
SELECT *
FROM focos_calor
WHERE fecha_adq BETWEEN '2024-01-01' AND '2024-03-31';

EXPLAIN ANALYZE
SELECT *
FROM meteo_diario
WHERE id_punto = 1
  AND tipo_dato = 'historico'
ORDER BY fecha DESC
LIMIT 90;
```

Evidencia esperada:

- con indices, el plan debe usar busqueda por fecha o clave compuesta cuando aplique;
- sin indices, el plan tiende a `Seq Scan` sobre tablas completas;
- la mejora se reporta comparando `Execution Time`.

## Riesgos y limites de la medicion

Las mediciones anteriores usan Parquet local como evidencia reproducible aun sin levantar
PostgreSQL/MongoDB. Para el informe final, conviene complementarlas con tiempos reales
de motor usando `EXPLAIN ANALYZE` en PostgreSQL y `.explain("executionStats")` en MongoDB.
La conclusion actual es valida para demostrar capacidad analitica local y dimensionar SLA,
pero no reemplaza una prueba remota en UTEC si el tribunal exige infraestructura integrada.
