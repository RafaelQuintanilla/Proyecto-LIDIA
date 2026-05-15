# Matriz de cumplimiento contra consigna 2026

Fuente oficial revisada: `Proyecto_Ingenieria_de_Datos_2026.pdf`.

Fecha de revision operativa: 2026-05-15.

Estados:

- **Cumplido**: existe implementacion o evidencia directa en el repositorio.
- **Parcial**: existe diseno, documentacion o implementacion incompleta.
- **Pendiente**: falta evidencia suficiente para defensa o entrega final.

## Requisitos transversales

| Requisito de la consigna | Estado | Evidencia actual | Accion de cierre |
|---|---:|---|---|
| Problema real con datos abiertos | Cumplido | `docs/PROYECTO_FINAL_EC1_EC2.md`, `docs/INFORME_EC1.md` | Mantener alcance oficial Uruguay, Brasil y Argentina en todos los documentos. |
| Arquitectura multicapa | Cumplido | `README.md`, `docs/ARQUITECTURA.md`, `docs/figures/` | Revisar que los diagramas reflejen el alcance final de 3 paises. |
| Persistencia poliglota SQL + NoSQL | Cumplido | PostgreSQL en `sql/`, MongoDB en `nosql/`, loaders en `etl/load/` | Alinear el relato MySQL/PostgreSQL: modelo teorico vs implementacion operativa. |
| Python para ETL | Cumplido | `etl/extract/`, `etl/transform/`, `etl/load/`, `etl/scheduler.py` | Dejar una guia de ejecucion unica y corta para la defensa. |
| Idempotencia del pipeline | Cumplido | `etl/load/load_postgres.py`, `tests/test_calidad_datos.py`, `tests/resultados_tests.json` | En defensa mostrar dos corridas o el reporte con 17/17 PASS. |
| CDC / carga incremental | Cumplido | `etl/scheduler.py`, tests `cdc_detecta_nuevos` y `cdc_detecta_modificacion` | Agregar evidencia breve de impacto en SQL y Mongo si se pide final completo. |
| Calidad de datos cuantitativa | Cumplido | `tests/test_calidad_datos.py`, `tests/resultados_tests.json` | Mantener reporte actualizado antes de entregar. |
| Dashboard Streamlit | Cumplido | `dashboard/app.py`, `dashboard/db.py`; verificado en `http://localhost:8501` | Capturar evidencia visual para informe/defensa. |
| Docker | Parcial | `docker/docker-compose.yml`, `docker/Dockerfile.streamlit` | Verificar `docker compose up -d` completo y registrar evidencia. |
| Replicacion en ambos motores | Parcial | `docs/REPLICACION_Y_SHARDING.md` define arquitectura PostgreSQL y MongoDB; no esta configurada en `docker-compose.yml` | Si el tribunal exige replica real, implementar compose especifico con primary/replica y replica set. |
| Sharding o simulacion de alto volumen | Cumplido | `scripts/simular_sharding.py`, `reports/sharding_simulado_ultimo.json`, `docs/REPLICACION_Y_SHARDING.md` | Mantener reporte actualizado si cambian datos FIRMS. |
| Despliegue hibrido in situ + cloud | Parcial | `docs/DESPLIEGUE_HIBRIDO.md`, `scripts/deploy.sh`, `config/utec.env.example` | Falta evidencia real de UTEC + cloud ejecutandose integrados. |
| Rendimiento medido | Cumplido | `scripts/medir_rendimiento.py`, `reports/rendimiento_ultimo.json`, `docs/SLA_Y_RENDIMIENTO.md` | Complementar con `EXPLAIN ANALYZE` si PostgreSQL esta activo. |
| SLA definido y evaluado | Cumplido | `docs/SLA_Y_RENDIMIENTO.md` | Recalcular antes de la entrega final. |
| Seguridad: roles, permisos, vistas | Parcial | `sql/ddl/01_roles.sql`, `sql/ddl/04_vistas.sql`, `.env.example`, `docs/SEGURIDAD_BACKUP_GOBERNANZA.md` | Cambiar passwords de ejemplo en entorno real y verificar que `.env` no se commitea. |
| Backup y recuperacion | Parcial | `backups/backup.sh`, `backups/restore.sh`, `docs/SEGURIDAD_BACKUP_GOBERNANZA.md` | Ejecutar backup/restore real y guardar conteos antes/despues. |
| Gobernanza y etica del dato | Cumplido | `docs/SEGURIDAD_BACKUP_GOBERNANZA.md`, `docs/PROYECTO_FINAL_EC1_EC2.md` | Reforzar en defensa oral con limitaciones de FIRMS/CAMS. |

## EC1 - Definicion del problema y analisis inicial

| Requisito EC1 | Estado | Evidencia actual |
|---|---:|---|
| Introduccion al dominio | Cumplido | `docs/INFORME_EC1.md`, `docs/PROYECTO_FINAL_EC1_EC2.md` |
| Contexto, actores, variables, dimension temporal y espacial | Cumplido | `docs/INFORME_EC1.md`, `docs/PROYECTO_FINAL_EC1_EC2.md` |
| Problema en 1-2 parrafos con alcance claro | Cumplido | `docs/PROYECTO_FINAL_EC1_EC2.md` |
| Objetivo general y 3 a 6 objetivos especificos | Cumplido | `docs/INFORME_EC1.md` |
| Minimo 3 fuentes reales y heterogeneas | Cumplido | FIRMS, Open-Meteo, CAMS, CHIRPS, MODIS |
| Ficha por fuente: origen, enlace, acceso, formato, volumen, frecuencia, granularidad, variables, limites | Cumplido | `docs/FUENTES_Y_DATOS.md`, `docs/PROYECTO_FINAL_EC1_EC2.md` |
| Exploracion preliminar real | Cumplido | `docs/INFORME_EC1.md`, extractores y datos procesados |
| Calidad preliminar: completitud, unicidad, consistencia, validez | Cumplido | `tests/test_calidad_datos.py`, `tests/resultados_tests.json` |
| Viabilidad SQL + NoSQL | Cumplido | `docs/ARQUITECTURA.md`, anexos A y B |
| Al menos 10 preguntas analiticas | Cumplido | `docs/PROYECTO_FINAL_EC1_EC2.md`, `sql/queries/01_analiticas.sql` |
| Arquitectura preliminar con fuentes -> ingesta -> procesamiento -> SQL -> NoSQL -> analitica | Cumplido | `docs/figures/`, `README.md` |

## EC2 - Diseno de la solucion

| Requisito EC2 | Estado | Evidencia actual | Accion de cierre |
|---|---:|---|---|
| Diagrama ER/EER y explicacion formal | Parcial | `docs/figures/figura_4_esquema_estrella.svg`, `docs/PROYECTO_FINAL_EC1_EC2.md` | Confirmar que figura y texto cubren ER/EER formal, no solo estrella. |
| Transformacion al modelo relacional | Cumplido | `docs/ANEXO_A_DDL_MYSQL.md`, `sql/ddl/02_schema.sql` | Aclarar equivalencia MySQL/PostgreSQL. |
| Normalizacion explicita y justificada | Parcial | `docs/PROYECTO_FINAL_EC1_EC2.md` | Hacer visible una subseccion de normalizacion si no esta marcada. |
| Esquema fisico preliminar | Cumplido | `sql/ddl/02_schema.sql`, `sql/ddl/03_indices.sql` |
| Modelo NoSQL | Cumplido | `nosql/schemas/`, `docs/ANEXO_B_JSON_SCHEMA_MONGODB.md` |
| Arquitectura detallada | Cumplido | `docs/ARQUITECTURA.md`, `docs/figures/figura_5_arquitectura_detallada.svg` |
| Diseno detallado del ETL | Cumplido | `docs/PROYECTO_FINAL_EC1_EC2.md`, `etl/` |
| Constraints SQL y JSON Schema NoSQL | Cumplido | `sql/ddl/02_schema.sql`, `nosql/schemas/` |
| Metricas preliminares y KPIs | Cumplido | `dashboard/app.py`, `docs/PROYECTO_FINAL_EC1_EC2.md` |
| Trade-offs y alternativas | Cumplido | `docs/PROYECTO_FINAL_EC1_EC2.md` |

## EC3 - Implementacion

| Requisito EC3 | Estado | Evidencia actual | Accion de cierre |
|---|---:|---|---|
| DDL completo con integridad, restricciones e indices | Cumplido | `sql/ddl/01_roles.sql` a `04_vistas.sql` |
| Carga real mediante ETL | Cumplido | `etl/load/load_postgres.py`, `etl/load/load_mongo.py` |
| Validacion post-carga | Cumplido | `tests/test_calidad_datos.py` |
| NoSQL con datos reales y consultas representativas | Parcial | `nosql/queries/01_consultas.js`, `etl/load/load_mongo.py` | Verificar colecciones locales/remotas y guardar evidencia de conteos. |
| ETL modular con errores, logging y config externa | Cumplido | `etl/`, `config/settings.py`, `etl/utils/logger.py`, `config/utec.env.example` |
| Automatizacion reproducible | Cumplido | `etl/scheduler.py`, scripts en `scripts/` |
| CDC funcional: inicial, incremental, insercion y modificacion | Cumplido | Tests 17/17 PASS el 2026-05-15 |
| Testing de calidad, idempotencia y CDC | Cumplido | `tests/test_calidad_datos.py`, `tests/resultados_tests.json` |
| Registro estructurado de tests | Cumplido | `tests/resultados_tests.json`, `logs/sinia_2026-05-15.json` |
| Seguridad de BD y pipeline | Parcial | Roles SQL, vistas, `.env.example` | Revisar passwords de ejemplo y documentar privilegio minimo. |
| Backup de BD y config | Parcial | `backups/backup.sh`, `backups/restore.sh` | Ejecutar prueba o agregar evidencia. |
| Dashboard con 7 KPIs, 2 agregaciones temporales y 2 comparaciones | Cumplido | `dashboard/app.py` | Capturar pantallas y asociarlas a preguntas. |
| Docker | Parcial | Compose existe | Ejecutar compose completo y registrar salida. |
| Arquitectura hibrida | Parcial | `docs/DESPLIEGUE_HIBRIDO.md`, `scripts/deploy.sh`, `config/utec.env.example` | Falta evidencia de in situ + cloud integrados. |
| Rendimiento preliminar | Cumplido | `scripts/medir_rendimiento.py`, `reports/rendimiento_ultimo.json`, `docs/SLA_Y_RENDIMIENTO.md` | Complementar con tiempos de motor si PostgreSQL/Mongo estan activos. |

## Etapa final - Evaluacion, informe y defensa

| Requisito final | Estado | Evidencia actual | Accion de cierre |
|---|---:|---|---|
| Optimizacion con evidencia antes/despues | Parcial | `docs/SLA_Y_RENDIMIENTO.md`, indices en `sql/ddl/03_indices.sql` | Falta `EXPLAIN ANALYZE` antes/despues sobre PostgreSQL activo. |
| Evaluacion completa de rendimiento | Parcial | `reports/rendimiento_ultimo.json`, `docs/SLA_Y_RENDIMIENTO.md` | Falta medicion remota/SQL vs NoSQL con motores activos. |
| Comparacion SQL vs NoSQL | Parcial | `sql/queries/01_analiticas.sql`, `nosql/queries/01_consultas.js`, `docs/CORRESPONDENCIA_PREGUNTAS_CONSULTAS_DASHBOARD.md` | Ejecutar tiempos comparables en motores activos. |
| Definicion y evaluacion de SLA | Cumplido | `docs/SLA_Y_RENDIMIENTO.md` | Recalcular si cambia volumen o entorno. |
| Metricas definitivas de calidad y evolucion EC1/EC3/final | Parcial | Tests actuales y documentos EC1 | Comparar resultados preliminares vs 2026-05-15 en informe final. |
| Evidencia final de idempotencia y CDC | Cumplido | `tests/resultados_tests.json` | Complementar con captura o tabla en informe final. |
| Resultados consolidados: preguntas -> consultas -> visualizaciones -> interpretacion -> limites | Cumplido | `docs/CORRESPONDENCIA_PREGUNTAS_CONSULTAS_DASHBOARD.md`, `sql/queries/01_analiticas.sql`, dashboard | Copiar tabla al informe final. |
| Evaluacion critica y trabajo futuro | Parcial | `docs/PROYECTO_FINAL_EC1_EC2.md` | Actualizar con problemas no resueltos reales. |
| Informe final segun modelo LIDIA | Parcial | `Proyecto_EC1_EC2_LIDIA_FINAL.docx`, `docs/PROYECTO_FINAL_EC1_EC2.md` | Integrar EC3/final: rendimiento, SLA, seguridad, backup, defensa. |
| Defensa oral: pipeline en vivo, CDC, metricas, dashboard | Cumplido | `docs/GUIA_DEFENSA_FINAL.md`, tests 17/17, dashboard local, reportes en `reports/` | Ensayar demo completa antes del tribunal. |

## Prioridad recomendada para cerrar brechas

1. **Arquitectura hibrida**: dejar evidencia de UTEC + cloud o ajustar el alcance con una prueba controlada.
2. **Replicacion real opcional**: implementar primary/replica si el tribunal exige ejecucion, no solo diseno.
3. **Backup/restore real**: ejecutar prueba y guardar conteos antes/despues.
4. **SQL vs NoSQL con motores activos**: medir consultas comparables.
5. **Informe final**: integrar EC3/final y limpiar contradicciones MySQL/PostgreSQL.
6. **Defensa**: preparar demo corta con comandos, salida esperada y plan B.

## Estado ejecutivo

El proyecto esta fuerte en dominio, fuentes reales, ETL, persistencia SQL/NoSQL, calidad de datos, idempotencia, CDC y dashboard. Desde el 2026-05-15 tambien cuenta con evidencia reproducible de rendimiento, SLA y sharding simulado. La parte mas sensible frente a la consigna oficial queda concentrada en infraestructura ejecutada: despliegue hibrido real, replicacion real si se exige, backup/restore probado y comparacion SQL vs NoSQL sobre motores activos.
