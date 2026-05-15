# Despliegue hibrido

La consigna pide integrar al menos un componente en infraestructura in situ y al menos
un componente en entorno cloud.

## Distribucion propuesta

| Componente | Ubicacion | Justificacion |
|---|---|---|
| PostgreSQL / Data Warehouse | Servidor institucional UTEC | Persistencia principal, datos auditables y cercania al entorno academico |
| MongoDB operacional | Servidor institucional UTEC o contenedor local controlado | Trazabilidad ETL, snapshots y alertas |
| Dashboard Streamlit | Cloud o maquina de demo | Acceso visual para defensa, consumo de datos persistidos |
| Repositorio Git | GitHub | Control de versiones y evidencia de cambios |
| ETL Python | Local/UTEC segun etapa | Puede correr donde tenga conectividad a APIs y bases |

## Evidencia existente

- `scripts/deploy.sh`
- `docs/desarrollo/13_DEPLOY_SERVIDOR_UTEC.md`
- `config/utec.env.example`
- `docker/docker-compose.yml`
- Dashboard verificado localmente en `http://localhost:8501` el 2026-05-15.

## Pasos de cierre para evidencia final

1. Levantar PostgreSQL y MongoDB en UTEC o confirmar bases existentes.
2. Ejecutar DDL:

```bash
psql -h <host-utec> -p <puerto> -d grp03db -f sql/ddl/01_roles.sql
psql -h <host-utec> -p <puerto> -d grp03db -f sql/ddl/02_schema.sql
psql -h <host-utec> -p <puerto> -d grp03db -f sql/ddl/03_indices.sql
psql -h <host-utec> -p <puerto> -d grp03db -f sql/ddl/04_vistas.sql
```

3. Cargar datos:

```bash
python etl/load/load_postgres.py
python etl/load/load_mongo.py
```

4. Levantar dashboard apuntando a UTEC:

```bash
streamlit run dashboard/app.py
```

5. Registrar evidencia:

- conteo de tablas PostgreSQL;
- conteo de colecciones MongoDB;
- captura del dashboard;
- salida de `python tests/test_calidad_datos.py`;
- URL o captura del componente cloud si se despliega Streamlit fuera de la maquina local.

## Estado actual

El proyecto tiene los archivos para un despliegue hibrido, pero la evidencia final depende
de ejecutar la carga en UTEC y publicar o mostrar el dashboard desde un entorno separado.
Para defensa local, se puede presentar Docker local + servidor UTEC como plan de despliegue,
pero para cumplir estrictamente la consigna final conviene guardar pruebas de conectividad
real.
