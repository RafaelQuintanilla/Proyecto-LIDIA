# 10 — Explicación del proyecto paso a paso

## 1. ¿Qué hace SINIA-UY?

Es un **sistema de monitoreo ambiental para detectar y predecir riesgo de incendios forestales en Uruguay** (con extensión a 6 países de Sudamérica). El sistema:

1. Descarga datos desde APIs públicas (NASA, Open-Meteo, CAMS).
2. Los limpia, transforma y calcula un **índice de riesgo de incendio**.
3. Los guarda en dos bases de datos: PostgreSQL (analítica) y MongoDB (operacional).
4. Los muestra en un **dashboard Streamlit** con mapa, series y alertas.
5. Se actualiza automáticamente mediante un scheduler.

## 2. Las capas del sistema (vista de pájaro)

```
[Capa 1] Fuentes externas (APIs públicas)
            ↓
[Capa 2] ETL en Python (extract → transform → load)
            ↓
[Capa 3] Almacenamiento (PostgreSQL + MongoDB)
            ↓
[Capa 4] Analítica + Dashboard Streamlit
            ↓
[Capa 5] Automatización (scheduler) + Tests de calidad + Backups
```

Cada capa está en una carpeta del proyecto. No hay magia: una capa lee la anterior y escribe a la siguiente.

## 3. Capa por capa con archivos reales

### 3.1 Fuentes externas — qué entra al sistema

| Fuente | Qué da | Granularidad | Cómo se accede |
|--------|--------|--------------|----------------|
| NASA FIRMS VIIRS NRT | Focos de calor de las últimas horas | Punto + hora | API REST con `FIRMS_MAP_KEY` |
| NASA FIRMS VIIRS SP | Archivo histórico de focos | Punto + hora | Misma API, modo archivo |
| Open-Meteo Forecast | Pronóstico meteo 7 días | Diario por punto | API REST sin clave |
| Open-Meteo Archive | Histórico meteorológico desde 1940 | Diario por punto | API REST sin clave |
| CAMS via Open-Meteo | Calidad del aire (PM10, PM2.5) | Horario por punto | API REST sin clave |
| CHIRPS (UCSB) | Precipitación mensual histórica | Mensual por punto | API ClimateSERV |
| MODIS MCD12Q1 | Cobertura vegetal anual | Anual por punto | NASA AppEEARS |

Todo configurado en `config/settings.py` (URLs base, listas de puntos, países, pesos del índice).

### 3.2 ETL — el corazón

Carpeta `etl/`. Tres etapas estrictamente separadas:

**Extract (`etl/extract/`)** — un archivo por fuente:
- `extract_firms.py` → descarga CSVs de FIRMS y los guarda en `data/raw/firms/`.
- `extract_meteo.py` → meteo histórico de las 19 ciudades a `data/raw/meteo/`.
- `extract_forecast.py` → pronóstico 7 días para los 5 puntos de Uruguay.
- `extract_cams.py` → calidad del aire horaria, guarda CSVs por ciudad.
- `extract_chirps.py` y `extract_modis.py` → fuentes complementarias.

Cada extractor: hace request HTTP → recibe JSON/CSV → guarda CSV crudo con el nombre del punto, sensor y rango de fechas. **Nunca modifica datos**, solo los baja.

**Transform (`etl/transform/`)** — un archivo por fuente:
- `transform_meteo.py` → lee meteo crudo, calcula los 4 componentes del índice de riesgo (temperatura, humedad, viento, sequía), los pondera (0.25/0.30/0.20/0.25) y clasifica en `bajo/moderado/alto/muy_alto`. Escribe a `data/processed/meteo_procesado_<ciudad>.parquet`.
- `transform_cams.py` → agrega CAMS horario a media diaria, calcula percentiles, marca si supera el límite OMS de 45 µg/m³ de PM10.
- `transform_firms.py` → normaliza coordenadas, asigna país por bounding box, normaliza confianza (l/n/h → 1/2/3).
- `transform_chirps.py` / `transform_modis.py` → procesado de las fuentes complementarias.

Salida estándar: archivos **Parquet** en `data/processed/` (formato comprimido y rápido).

**Load (`etl/load/`)** — dos destinos:
- `load_postgres.py` → lee los parquets y hace **UPSERT idempotente** a PostgreSQL. Si un registro ya existe (misma clave natural) se actualiza; si no, se inserta. Sin duplicados.
- `load_mongo.py` → escribe snapshots diarios, alertas y trazas de ejecución a MongoDB.

**Auditoría CDC** — cada ejecución registra en `etl_ejecuciones` cuántos registros se procesaron, insertaron, actualizaron y cuánto tardó. Esto es lo que se examina en defensa cuando preguntan "¿cómo sabés que no duplica?".

### 3.3 Almacenamiento — dos motores complementarios

**PostgreSQL (`sql/`)** — Data Warehouse analítico:

| Tabla | Tipo | Qué guarda |
|-------|------|-----------|
| `puntos_monitoreo` | Dimensión | 19 ciudades de monitoreo |
| `paises_referencia` | Dimensión | 7 países (BRA, BOL, PRY, ARG, CHL, PER, URY) |
| `focos_calor` | Hechos | Cada foco detectado por satélite |
| `meteo_diario` | Hechos | Meteo + índice de riesgo, histórico y forecast |
| `calidad_aire_diario` | Hechos | PM10, PM2.5, AQI por día/punto |
| `precipitacion_mensual` | Hechos | CHIRPS por punto/mes |
| `cobertura_vegetal` | Hechos | MODIS anual por punto |
| `etl_ejecuciones` | Auditoría | Cada corrida del pipeline |

Cada tabla tiene `CHECK` constraints, una `UNIQUE` para idempotencia y triggers de timestamp. Hay tres roles (`sinia_readonly`, `sinia_etl`, `sinia_admin`) con principio de mínimo privilegio.

Los archivos están organizados en orden de ejecución:
```
sql/ddl/
├── 01_roles.sql     ← roles + usuarios
├── 02_schema.sql    ← tablas con CHECKs y triggers
├── 03_indices.sql   ← índices analíticos
├── 04_vistas.sql    ← vistas para dashboard y seguridad
└── 05_migracion_sa.sql

sql/dml/
└── 01_seed_puntos.sql  ← carga inicial de los 19 puntos

sql/queries/
└── 01_analiticas.sql   ← 10 consultas representativas
```

Esto se ejecuta **automáticamente** en orden alfabético cuando Postgres arranca por primera vez gracias al volumen `docker-entrypoint-initdb.d/`.

**MongoDB (`nosql/`)** — base operacional flexible:

| Colección | Qué guarda | Por qué Mongo y no Postgres |
|-----------|-----------|-----------------------------|
| `focos_snapshots` | Un documento por día con todos los focos | Documento embebido evita JOINs |
| `alertas` | Eventos de riesgo (no son tabulares, varían en campos) | Esquema flexible |
| `ejecuciones_etl` | Traza con logs nested | Logs anidados se modelan mejor como JSON |

Tiene `nosql/schemas/*.json` (JSON Schema para validación), `nosql/init/01_setup_mongo.js` (índices y validators) y `nosql/queries/01_consultas.js` (consultas representativas).

### 3.4 Dashboard — Streamlit (`dashboard/`)

- `app.py` → la UI: filtros por fecha y país, mapa de focos, serie temporal de índice, panel de alertas, tabla con detalles.
- `db.py` → wrapper de conexión a Postgres y Mongo (usa `PG_CONFIG` y `MONGO_CONFIG` de settings).

Se levanta con `streamlit run dashboard/app.py` (local) o vía contenedor Docker (`docker compose up streamlit`).

### 3.5 Analítica avanzada (`analytics/`)

- `riesgo_analytics.py` → consultas analíticas, clustering, detección de anomalías con scikit-learn.

### 3.6 Tests de calidad (`tests/`)

`tests/test_calidad_datos.py` — 17 tests categorizados:

- **Completitud** — sin nulos en campos críticos.
- **Unicidad** — sin duplicados por clave natural.
- **Consistencia** — coordenadas dentro de Uruguay, humedad 0–100%, índice 0–1.
- **Validez** — dominios permitidos (`bajo/moderado/alto/muy_alto`, etc.).
- **Idempotencia** — doble carga produce el mismo resultado.
- **CDC** — detecta correctamente nuevos registros y modificaciones.

Genera `tests/resultados_tests.json` con métricas. **Última ejecución: 2026-03-19, 17/17 PASS.**

### 3.7 Scheduler y automatización (`etl/scheduler.py`)

Usa APScheduler para correr extractores y loaders periódicamente. En servidor se levanta como proceso de fondo (o servicio systemd) para mantener los datos frescos.

### 3.8 Backups (`backups/`)

- `backup.sh` → `pg_dump` de Postgres + `mongodump` de Mongo + tar de configs, todo timestampeado.
- `restore.sh` → restaura desde una carpeta de backup.

### 3.9 Logs (`logs/`)

Cada módulo loguea en JSON estructurado vía `etl/utils/logger.py`. Un log por día (`sinia_YYYY-MM-DD.json`). Esto permite hacer `jq` sobre los logs y construir métricas operacionales.

### 3.10 Docker (`docker/`)

- `docker-compose.yml` → orquesta los 3 servicios (postgres, mongo, streamlit).
- `Dockerfile.streamlit` → imagen del dashboard.
- `.env` → credenciales (NO se sube a git).
- `.env.example` → plantilla del `.env`.

## 4. Flujo de datos de punta a punta (ejemplo)

Querés saber el riesgo de incendio en Rivera para hoy. Esto es lo que pasa por debajo:

```
1. scheduler.py dispara el ciclo a las 03:00 UTC
   ↓
2. extract_forecast.py llama Open-Meteo con (lat=-30.91, lon=-55.55)
   → guarda data/raw/meteo/forecast_rivera_20260511_0300.csv
   ↓
3. extract_cams.py llama CAMS Air Quality para la misma fecha
   → guarda data/raw/cams/cams_rivera_hourly_2026-05-11.csv
   ↓
4. transform_meteo.py lee el forecast, calcula índice:
   indice = temp×0.25 + humedad×0.30 + viento×0.20 + sequia×0.25
   → guarda data/processed/meteo_procesado_rivera.parquet
   ↓
5. transform_cams.py agrega 24 valores horarios → 1 diario, marca alerta si PM10 > 45
   ↓
6. load_postgres.py hace UPSERT en meteo_diario y calidad_aire_diario
   ↓
7. load_mongo.py guarda snapshot diario en focos_snapshots y
   si hay riesgo "alto/muy_alto" inserta un documento en alertas
   ↓
8. Se registra la ejecución en etl_ejecuciones (Postgres) y
   ejecuciones_etl (Mongo)
   ↓
9. dashboard/app.py refresca: el usuario ve el índice de hoy en Rivera
```

Si algo falla en cualquier paso, el logger captura el error con stack trace y la auditoría queda en estado `error` o `parcial` con el mensaje.

## 5. Decisiones de diseño que se preguntan en defensa

| Decisión | Razón corta |
|----------|------------|
| ¿Por qué dos bases (Postgres + Mongo)? | Complementariedad: Postgres es OLAP estructurado; Mongo es operacional con esquema variable (logs, alertas, snapshots). |
| ¿Por qué Parquet entre transform y load? | Compresión + columnar = lectura analítica rápida; preserva tipos exactos. |
| ¿Por qué UPSERT y no INSERT? | Idempotencia: rerunnable sin duplicados. Habilita reintentos seguros. |
| ¿Por qué CHECK constraints en las tablas? | Calidad de datos al borde: nada inválido entra a la BD aunque el ETL falle. |
| ¿Por qué auditoría en `etl_ejecuciones`? | Permite responder "¿cuándo corrió por última vez X y con qué resultado?" sin leer logs. |
| ¿Por qué tres roles Postgres? | Principio de mínimo privilegio: el dashboard solo lee, el ETL no borra ni hace DDL. |
| ¿Por qué no sharding? | Volumen actual (~365 reg/año/tabla) no lo justifica. Se documenta la estrategia hipotética con `fecha` como shard key. |

## 6. Lo que no hace (alcance)

- **No es modelo predictivo** — el índice es un score determinístico, no un ML predictor de incendios.
- **No tiene autenticación en el dashboard** — corre en red interna, no en internet abierto.
- **No tiene alta disponibilidad** — una sola instancia de cada servicio.
- **No procesa imágenes satelitales raw** — usa productos derivados ya procesados por NASA/Copernicus.

Estos límites están bien para un proyecto académico y se mencionan como "trabajos futuros" en la defensa.

---

**Próximo paso:** [11_SETUP_LOCAL.md](11_SETUP_LOCAL.md) — levantar todo esto en tu PC.
