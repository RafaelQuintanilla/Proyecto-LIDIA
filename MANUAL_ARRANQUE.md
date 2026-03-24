# SINIA-SA — Manual de Arranque
**UTEC · Ingeniería de Datos e IA · 2026**

Seguí estos pasos en orden cada vez que quieras levantar el proyecto.

---

## Paso 1 — Abrir Git Bash

Abrí **Git Bash** (no PowerShell ni CMD).
Todo lo que sigue se escribe ahí.

---

## Paso 2 — Iniciar PostgreSQL

```bash
"/c/Program Files/PostgreSQL/16/bin/pg_ctl" start \
  -D "/c/Program Files/PostgreSQL/16/data" \
  -l "/c/Program Files/PostgreSQL/16/data/log/pg_start.log"
```

Verificar que arrancó:

```bash
PGPASSWORD=postgres_super_2026 "/c/Program Files/PostgreSQL/16/bin/pg_isready" -h localhost -p 5432
```

Debe decir: `localhost:5432 - accepting connections`

---

## Paso 3 — Iniciar MongoDB

```bash
"/c/Program Files/MongoDB/Server/6.0/bin/mongod.exe" \
  --dbpath "C:/Users/rqf18/mongodb_data" \
  --logpath "C:/Users/rqf18/mongodb_logs/mongod.log" \
  --port 27017 \
  --bind_ip 127.0.0.1 \
  --logappend &
```

Verificar que arrancó:

```bash
curl -s --max-time 3 http://localhost:27017
```

Debe decir algo con "MongoDB over HTTP".

---

## Paso 4 — Ir a la carpeta del proyecto

```bash
cd "/c/Users/rqf18/OneDrive/Documentos/api/Custom Office Templates/EjercicioSQL/Escritorio/PROYECTO INGIENERIA DE DATOS/SONIA-UY"
```

---

## Paso 5 — Iniciar el Dashboard

En una **nueva pestaña de Git Bash** (o en segundo plano):

```bash
python -m streamlit run dashboard/app.py --server.port 8502
```

Luego abrir en el navegador: **http://localhost:8502**

---

## Paso 6 — Iniciar el Scheduler ETL

En otra **nueva pestaña de Git Bash**:

```bash
python -m etl.scheduler
```

El scheduler descarga datos automáticamente:
- Focos FIRMS: cada 3 horas
- Pronóstico meteorológico: cada 1 hora
- Calidad del aire CAMS: cada 1 hora

Para detenerlo: `Ctrl + C`

---

## Resumen rápido (todo junto)

```
Pestaña 1 → PostgreSQL + MongoDB (Pasos 2 y 3)
Pestaña 2 → Dashboard           (Paso 5)
Pestaña 3 → Scheduler ETL       (Paso 6)
```

---

## Datos de conexión

| Sistema | Host | Puerto | Usuario | Contraseña | Base |
|---|---|---|---|---|---|
| PostgreSQL | localhost | 5432 | postgres | postgres_super_2026 | sinia_uy |
| MongoDB | localhost | 27017 | — (sin auth) | — | sinia_uy |

---

## Comandos útiles

**Ver cuántos focos hay cargados:**
```bash
PGPASSWORD=postgres_super_2026 "/c/Program Files/PostgreSQL/16/bin/psql" \
  -U postgres -d sinia_uy \
  -c "SELECT COUNT(*) FROM focos_calor;"
```

**Refrescar la vista materializada (si hay datos nuevos):**
```bash
PGPASSWORD=postgres_super_2026 "/c/Program Files/PostgreSQL/16/bin/psql" \
  -U postgres -d sinia_uy \
  -c "REFRESH MATERIALIZED VIEW CONCURRENTLY mv_focos_por_pais_mes;"
```

**Ver logs del scheduler:**
```bash
cat /tmp/scheduler.log | tail -30
```

**Detener PostgreSQL:**
```bash
"/c/Program Files/PostgreSQL/16/bin/pg_ctl" stop \
  -D "/c/Program Files/PostgreSQL/16/data"
```

---

## Estado actual de datos (2026-03-20)

| Tabla | Registros |
|---|---|
| focos_calor | 19,510,222 (2018–2024) |
| meteo_diario | 46,117 |
| calidad_aire_diario | 41,256+ |
| precipitacion_mensual | 1,404 |
| cobertura_vegetal | 126 |
| MongoDB focos_snapshots | 2,174 docs (2018–2023) |
