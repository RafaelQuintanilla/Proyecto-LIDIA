# MongoDB

PostgreSQL conserva el Data Warehouse y las consultas analiticas. MongoDB se
limita a documentos variables: payloads crudos por fuente, metadata de
ejecucion, logs, rechazos con payload original, snapshots FIRMS resumidos y
metadata de calidad del aire CAMS/Open-Meteo Air Quality cuando exista carga
validada. Estos documentos admiten distintos
detalles por fuente sin modificar el esquema estrella.

`mongo_schema.json` contiene los validadores JSON Schema y
`mongo_queries.js` consultas representativas. No se almacenan credenciales ni
se propone sharding para el servidor institucional.
