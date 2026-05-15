# 15 — Checklist diario

Hoja de cabecera que abrís cada vez que te sentás a trabajar en el proyecto. Hacelo en orden y no salteés pasos las primeras dos semanas; después se vuelve automático.

## Antes de empezar a programar

- [ ] Abrir terminal en la raíz del proyecto.
- [ ] `git status` — ¿estoy en una rama limpia? Si hay cambios sueltos, decidí qué hacer con ellos antes de seguir.
- [ ] `git pull origin dev` (o `main` si estás en `main`) — traer cambios de otros entornos.
- [ ] Si trabajás con docker: `docker compose ps` — ¿Postgres y Mongo `healthy`? Si no, `docker compose up -d postgres mongo`.
- [ ] Activar venv: `.venv\Scripts\activate` (Windows) o `source .venv/bin/activate` (Linux).
- [ ] `pip install -r requirements.txt --quiet` — por si entraron deps nuevas.

## Al empezar una tarea nueva

- [ ] Crear rama: `git checkout -b feature/<descripcion-corta>` o `fix/<descripcion>`.
- [ ] Anotar en `docs/desarrollo/bitacora/<fecha>.md` qué vas a hacer y por qué.
- [ ] Si la tarea implica una decisión técnica nueva (no un fix puntual), abrir borrador de ADR en `docs/desarrollo/adr/`.

## Durante el desarrollo

- [ ] Cada 30–60 min: `git status` + commit pequeño con mensaje claro.
- [ ] Si tocás SQL: probá la query en `psql`/DBeaver antes de meterla al código.
- [ ] Si tocás un extractor: corré el script aislado y mirá el archivo de salida.
- [ ] Si tocás un transform: validá visualmente el parquet (con pandas) antes de cargarlo.
- [ ] Si tocás un loader: corrélo dos veces seguidas para verificar idempotencia.

## Antes de cerrar la sesión

- [ ] Correr los tests: `python tests/test_calidad_datos.py`.
- [ ] Si fallaron tests, decidir: arreglo ahora o lo dejo documentado como pendiente.
- [ ] Actualizar `docs/desarrollo/bitacora/<fecha>.md` con: qué hice, qué aprendí, qué quedó pendiente, próximo paso.
- [ ] Si la tarea está completa: PR a `dev`, mergear, borrar rama local y remota.
- [ ] Si la tarea está a medias: commit con mensaje "WIP: ..." y push a tu rama remota (backup).
- [ ] `docker compose stop` si vas a apagar la máquina (los datos persisten en el volumen).

## Antes de pushear a `main` (= deploy a UTEC)

- [ ] Todos los tests pasan en local (17/17 PASS).
- [ ] El dashboard levanta sin errores en local.
- [ ] El scheduler corrió al menos un ciclo completo localmente.
- [ ] El CHANGELOG.md tiene una entrada nueva con la versión y los cambios.
- [ ] Tag de versión: `git tag -a v1.x.y -m "..."`.
- [ ] `git push origin main --tags`.
- [ ] Conectarte al servidor UTEC y correr `bash scripts/deploy.sh`.
- [ ] Verificar que el dashboard remoto responde y los tests pasan también allá.

## Una vez por semana

- [ ] Revisar `docs/desarrollo/bitacora/` y consolidar en `docs/desarrollo/reportes/<semana>.md`.
- [ ] Revisar tamaño de `data/` y `logs/` en el servidor. Rotar si es necesario.
- [ ] Verificar que el backup del servidor tiene archivos recientes.
- [ ] Probar restore en un entorno aislado (al menos una vez por mes).
- [ ] Revisar ADRs pendientes y completar las que se hayan quedado en borrador.

## Una vez por mes

- [ ] Actualizar dependencias: `pip list --outdated`, evaluar updates conservadores.
- [ ] Revisar logs de errores: ¿hay patrones recurrentes que justifican un runbook nuevo?
- [ ] Snapshot del repo (clone bare) en un USB externo, por si pasa algo con GitHub.
- [ ] Repasar `README.md`: ¿sigue describiendo lo que el sistema hace hoy?

## En caso de incidente en producción

1. **No entrar en pánico.** Los datos están en volúmenes persistentes y hay backup diario.
2. Mirar `logs/scheduler.log` y `logs/scheduler.error.log` en el servidor.
3. `docker compose logs <servicio> --tail 100` para el contenedor afectado.
4. Buscar runbook específico en `docs/desarrollo/runbooks/`.
5. Si no hay runbook para el síntoma: documentá el incidente en `docs/desarrollo/bitacora/<fecha>.md` mientras lo resolvés, y crealo después.
6. Si tenés que rollback: `git checkout v<version-anterior>` en el servidor y volver a correr `bash scripts/deploy.sh`.

---

**Atajo de "está todo bien"**: si al final del día podés decir "sí" a estas tres preguntas, no te debe el trabajo nada hoy:

1. ¿Todo lo que cambié está commiteado y pusheado?
2. ¿Los tests pasan?
3. ¿La bitácora del día tiene al menos 3 líneas?
