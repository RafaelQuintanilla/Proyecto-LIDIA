# Guia de defensa final

Objetivo: demostrar que SINIA-UY es un sistema funcional de ingenieria de datos,
con datos reales, ETL reproducible, persistencia SQL/NoSQL, CDC, calidad, rendimiento
y dashboard.

## 1. Apertura

Mensaje breve:

> SINIA-UY integra datos satelitales y meteorologicos para monitorear riesgo de
> incendios forestales en Uruguay, Brasil y Argentina. El sistema usa Python para
> ETL, PostgreSQL como Data Warehouse, MongoDB para trazabilidad/snapshots/alertas
> y Streamlit para la capa analitica.

## 2. Comandos de demo

Desde la raiz del proyecto:

```bash
python tests/test_calidad_datos.py
```

Resultado esperado:

```text
Resultado: 17 PASS / 0 FAIL
```

Medir rendimiento:

```bash
python scripts/medir_rendimiento.py
```

Resultado esperado:

```text
Reporte generado: reports/rendimiento_<fecha>.json
```

Simular sharding:

```bash
python scripts/simular_sharding.py
```

Resultado esperado:

```text
filas_firms: 1836537
sql_shards: 4
mongo_shards_logicos: 36
```

Levantar dashboard:

```bash
streamlit run dashboard/app.py --server.port 8501
```

Abrir:

```text
http://localhost:8501
```

## 3. Evidencia que conviene mostrar

| Tema | Archivo |
|---|---|
| Consigna vs cumplimiento | `docs/MATRIZ_CUMPLIMIENTO_CONSIGNA_2026.md` |
| SLA y rendimiento | `docs/SLA_Y_RENDIMIENTO.md` |
| Reporte rendimiento | `reports/rendimiento_ultimo.json` |
| Replicacion y sharding | `docs/REPLICACION_Y_SHARDING.md` |
| Reporte sharding | `reports/sharding_simulado_ultimo.json` |
| Seguridad y backup | `docs/SEGURIDAD_BACKUP_GOBERNANZA.md` |
| Preguntas -> consultas -> dashboard | `docs/CORRESPONDENCIA_PREGUNTAS_CONSULTAS_DASHBOARD.md` |
| Despliegue hibrido | `docs/DESPLIEGUE_HIBRIDO.md` |

## 4. Puntos tecnicos para defender

### Por que SQL y NoSQL

PostgreSQL guarda hechos estructurados y consultables por agregaciones temporales:
focos, meteorologia, calidad del aire y vistas analiticas.

MongoDB guarda documentos variables: ejecuciones ETL, alertas y snapshots diarios,
donde conviene flexibilidad sin joins.

### CDC e idempotencia

CDC usa watermark temporal en `etl/scheduler.py`. La idempotencia se sostiene con claves
naturales, upserts/deduplicacion y tests automaticos. La evidencia principal es
`tests/resultados_tests.json`.

### Rendimiento

El SLA de consultas analiticas es 3000 ms. La peor consulta local medida fue focos por
mes sobre 1.836.537 registros, con 490.622 ms promedio. Cumple.

### Sharding

No se activa sharding real porque el volumen academico cabe en un nodo. Se simula y se
elige:

- SQL: `focos_calor` particionada por `fecha_adq`.
- MongoDB: `focos_snapshots` con `{ fecha: 1, pais: "hashed" }`.

### Replicacion

La arquitectura define:

- PostgreSQL primario + replicas de lectura por WAL streaming.
- MongoDB replica set de tres miembros.

Si preguntan por ejecucion real, responder con honestidad: la evidencia actual es
arquitectonica y reproducible; la configuracion real queda como paso de infraestructura
si el entorno UTEC/cloud lo requiere.

## 5. Plan B de demo

Si PostgreSQL o MongoDB no levantan:

1. Mostrar que el dashboard tiene fallback a Parquet.
2. Ejecutar `python tests/test_calidad_datos.py`.
3. Mostrar `reports/rendimiento_ultimo.json`.
4. Mostrar `reports/sharding_simulado_ultimo.json`.
5. Explicar que la arquitectura de persistencia esta implementada en `sql/`, `nosql/`
   y `etl/load/`, aunque la demo visual use datos procesados.

## 6. Cierre

Mensaje breve:

> El sistema cumple el ciclo de vida completo del dato: fuentes reales, extraccion,
> transformacion, carga, calidad, CDC, trazabilidad, analitica y visualizacion. Las
> brechas restantes son de infraestructura final: ejecutar replica real, evidencia
> UTEC/cloud y restore probado en entorno final.
