# 14 — Plan de documentación de desarrollo en paralelo

> El proyecto ya tiene documentación académica (defensa, informe EC1/EC2, arquitectura). Esta guía es **distinta**: cubre la documentación de **desarrollo y operación** que vas a ir escribiendo mientras programás. Sirve para vos en 3 meses, para el tribunal de defensa, para tu compañero y para quien tome el proyecto después.

## 1. Principio rector

**Escribí la documentación mientras hacés el cambio, no después.** Cinco minutos al cerrar cada sesión vale más que dos días de "ahora sí me siento a documentar" al final.

Tres preguntas para cada documento:

1. ¿Quién lo va a leer? (vos en el futuro, otro dev, el tribunal)
2. ¿Qué pregunta concreta responde? (no escribir documentación abstracta)
3. ¿En cuánto tiempo el lector se desbloquea? (objetivo: menos de 10 minutos)

Si no podés responder estas tres, no escribas todavía.

## 2. Estructura propuesta para `docs/desarrollo/`

```
docs/desarrollo/
├── 00_INDICE.md                           ← ya creado
├── 10_EXPLICACION_PROYECTO_PASO_A_PASO.md ← ya creado
├── 11_SETUP_LOCAL.md                      ← ya creado
├── 12_WORKFLOW_GIT.md                     ← ya creado
├── 13_DEPLOY_SERVIDOR_UTEC.md             ← ya creado
├── 14_PLAN_DOCUMENTACION_PARALELA.md      ← este archivo
├── 15_CHECKLIST_DIARIO.md                 ← ya creado
│
├── adr/                                   ← decisiones de arquitectura
│   ├── 0001-elegimos-postgres-y-mongo.md
│   ├── 0002-parquet-como-formato-intermedio.md
│   └── 0003-apscheduler-en-vez-de-airflow.md
│
├── runbooks/                              ← qué hacer cuando algo pase
│   ├── etl-fallo-firms.md
│   ├── postgres-no-arranca.md
│   ├── disco-lleno.md
│   └── restaurar-backup.md
│
├── bitacora/                              ← log diario de desarrollo
│   ├── 2026-05-11.md
│   ├── 2026-05-12.md
│   └── ...
│
└── reportes/                              ← snapshots periódicos
    ├── 2026-05-semana1-estado.md
    └── ...
```

## 3. ADR — Architecture Decision Records

Una ADR documenta **una decisión técnica importante**, **por qué se tomó** y **qué se descartó**. Plantilla:

```markdown
# ADR 0001 — Elegimos PostgreSQL como Data Warehouse y MongoDB como base operacional

- **Estado**: aceptada
- **Fecha**: 2026-02-15
- **Decisores**: Rafael Q.

## Contexto
Necesitamos almacenar 3 tipos de datos: estructurados con esquema estable (focos,
meteo, calidad de aire), logs de ejecución con campos variables, y alertas con
estructura semi-libre. Una sola base obliga a comprometer algo.

## Decisión
Usar PostgreSQL para datos analíticos y MongoDB para datos operacionales/logs.

## Alternativas consideradas
1. **Solo PostgreSQL** con columnas JSONB para lo flexible.
   - Descartada: ETL más complejo, pierdes índices nativos sobre JSON anidado,
     no aporta diferenciación técnica frente al requisito de la materia.
2. **Solo MongoDB**.
   - Descartada: queries analíticas con JOINs son verbose y lentas en Mongo.
3. **Snowflake / BigQuery**.
   - Descartada: alcance académico, costo, complejidad operativa innecesaria.

## Consecuencias
- (+) Cada motor hace lo que mejor sabe.
- (+) La defensa puede justificar la elección con datos concretos.
- (−) Mantenimiento doble (dos backups, dos sets de credenciales).
- (−) ETL debe escribir a dos destinos — se mitiga con `etl/load/load_postgres.py`
  y `etl/load/load_mongo.py` separados e idempotentes.
```

**Reglas para ADRs**:

- Una por archivo, numerada.
- Cortas (1 página).
- Inmutables — si revisás la decisión, no editás la ADR vieja: agregás una nueva con `Estado: supersedes 0001`.

**ADRs que ya podrías escribir hoy con lo que ya hay implementado:**

1. PostgreSQL + MongoDB (justificación de complementariedad).
2. Parquet como formato intermedio (vs CSV).
3. APScheduler en vez de Airflow (alcance académico).
4. Streamlit en vez de Dash o React + API (simplicidad).
5. UPSERT por clave natural para idempotencia.
6. Docker Compose en vez de instalación nativa.
7. Tres roles Postgres con mínimo privilegio.
8. Pesos del índice de riesgo (0.25/0.30/0.20/0.25) — referencia INIA.

## 4. Runbooks — qué hacer cuando algo pasa

Un runbook es una **receta operativa para un incidente puntual**. Plantilla:

```markdown
# Runbook — ETL de FIRMS falla con timeout

## Síntoma
`extract_firms.py` aborta con `requests.exceptions.Timeout` o
`urllib3.exceptions.ReadTimeoutError`.

## Causa probable
- La API de FIRMS está saturada o caída temporalmente.
- La MAP_KEY excedió el límite diario (5000 transacciones/10min).
- Red del servidor sin acceso a `firms.modaps.eosdis.nasa.gov`.

## Diagnóstico (en orden)
1. Probar la URL directamente:
   ```
   curl -I "https://firms.modaps.eosdis.nasa.gov/api/area/csv/<MAP_KEY>/VIIRS_SNPP_NRT/-82,-56,-34,13/1"
   ```
   Si responde 200, la API está OK; si 401, MAP_KEY inválida; si 5xx, FIRMS down.

2. Ver cuántas transacciones llevamos hoy:
   ```
   curl "https://firms.modaps.eosdis.nasa.gov/mapserver/mapkey_status/?MAP_KEY=<...>"
   ```

3. Revisar el último log:
   ```
   tail -20 logs/sinia_$(date +%F).json
   ```

## Solución
- Si es timeout temporal: reintentar en 10 minutos (el scheduler lo hará solo).
- Si se excedió el límite: esperar al reset (ventana móvil de 10 min).
- Si MAP_KEY inválida: regenerar en https://firms.modaps.eosdis.nasa.gov/api/map_key/
  y actualizar `docker/.env` y `config/.env`. Reiniciar el scheduler.

## Cómo prevenir
- Cachear extracciones para no rehacer si la data ya está en `data/raw/`.
- Implementar backoff exponencial en `extract_firms.py`.
- Reducir el bbox a Uruguay si el sudamericano es demasiado.
```

**Runbooks prioritarios para SINIA-UY**:

| # | Runbook | Probabilidad de necesitarlo |
|---|---------|------------------------------|
| 1 | ETL de FIRMS falla con timeout | Alta — APIs satelitales fluctúan |
| 2 | Postgres no arranca después de reboot | Media |
| 3 | Mongo replica con autenticación fallida | Baja |
| 4 | Disco del servidor casi lleno | Media — logs crecen |
| 5 | Restaurar backup tras corrupción de datos | Baja |
| 6 | Dashboard muestra "No data" en producción | Media |
| 7 | Scheduler dejó de correr | Media |
| 8 | Test de calidad falla en CI | Alta — cada vez que cambies transform |

## 5. Bitácora diaria

Un archivo por día de trabajo, formato libre pero con esta estructura mínima:

```markdown
# 2026-05-11

## Qué hice
- Levanté Postgres y Mongo localmente con Docker.
- Corrí la primera carga del ETL.
- 17/17 tests PASS.
- Empecé a escribir la guía de desarrollo en docs/desarrollo/.

## Qué aprendí
- El init de Postgres solo corre en el primer arranque. Si edito el schema,
  tengo que aplicarlo con ALTER o `docker compose down -v`.
- `data/raw/` pesa ~50 MB después de extraer toda la histórica → confirmado que
  está bien excluido del `.gitignore`.

## Qué me trabó
- El healthcheck de Mongo tardó 45s la primera vez. Pensé que estaba roto.

## Próximo paso
- Inicializar git y subir a GitHub.
- Pedir datos del servidor UTEC al docente.
```

**Por qué importa**: cuando llegues a defensa o a un final de proyecto, tener 60 entradas como esta te da material concreto para responder "¿qué desafíos enfrentaste?", "¿cómo evolucionó tu decisión sobre X?", "¿cuánto te llevó implementar Y?".

## 6. Reportes semanales / por sprint

Cada viernes (o cierre de iteración), un archivo con:

- Lo que se completó.
- Lo que quedó pendiente y por qué.
- Decisiones tomadas (linkeadas a ADRs).
- Riesgos identificados.
- Métricas (tests passing, líneas de código, tablas con datos).

Esto sirve para informes parciales que pide la materia.

## 7. Docstrings dentro del código

Cada función pública del ETL debería tener un docstring corto:

```python
def calcular_indice_riesgo(temp: float, humedad: float, viento: float, sequia: float) -> tuple[float, str]:
    """Calcula el índice de riesgo de incendio.

    Suma ponderada de 4 componentes normalizados a [0,1].
    Pesos según metodología INIA: temp=0.25, humedad=0.30, viento=0.20, sequia=0.25.

    Args:
        temp: Componente de temperatura [0,1].
        humedad: Componente de humedad [0,1].
        viento: Componente de viento [0,1].
        sequia: Componente de sequía [0,1].

    Returns:
        Tupla (indice [0,1], nivel ['bajo','moderado','alto','muy_alto']).

    Raises:
        ValueError: si algún componente está fuera de [0,1].
    """
```

Para clases SQL, comentarios `COMMENT ON TABLE` y `COMMENT ON COLUMN` (ya están en `02_schema.sql`, mantenlos al día si agregás campos).

## 8. Mantener `README.md` actualizado

El `README.md` raíz es lo primero que ve cualquiera (incluido el tribunal). Mantenelo así:

- Una línea sobre qué hace el proyecto.
- Levantamiento rápido (3 comandos).
- Link al doc `00_INDICE.md` para detalle.
- Tabla de tests y estado.

Cuando cambies algo grande (nueva tabla, nueva API, nuevo deploy), actualizá el README en el mismo commit. **No dejes el README desincronizado del código.**

## 9. Material para la defensa académica (`docs/`)

La carpeta `docs/` actual ya tiene:

- `DEFENSA.md`
- `ARQUITECTURA.md`
- `FUENTES_Y_DATOS.md`
- `INFORME_EC1.md`
- `PROYECTO_FINAL_EC1_EC2.md`
- `CHECKLIST_CUMPLIMIENTO_EC1_EC2.md`
- `figures/*.svg`

**No mezcles**: la documentación académica vive en `docs/` y la operativa/desarrollo en `docs/desarrollo/`. Cuando termines, vas a tener:

```
docs/
├── (defensa académica)
└── desarrollo/
    └── (operación, runbooks, ADRs, bitácora)
```

Si la defensa pide "documentación de desarrollo", linkeás `docs/desarrollo/00_INDICE.md`.

## 10. Calendario sugerido para escribir la doc

Si vas a defender en, digamos, 6 semanas:

| Semana | Foco de documentación |
|--------|----------------------|
| 1 | Bitácora diaria. Crear `00_INDICE.md` (ya hecho). Empezar primeras 3 ADRs (las decisiones obvias). |
| 2 | Setup local + git workflow ya documentados. Empezar 2 runbooks (FIRMS, Postgres). |
| 3 | Deploy al servidor + runbook de backup. Tercera tanda de ADRs. |
| 4 | Reporte semanal. Refinar README. Docstrings en funciones clave. |
| 5 | Ensayo de defensa con la doc: ¿alguien externo levanta el proyecto siguiendo solo los docs? |
| 6 | Pulido final. PDF de informe. Checklist EC2. |

## 11. Reglas para que la documentación no se pudra

1. **Una sola fuente de verdad**: si el dato está en `config/settings.py`, no lo repitas hardcodeado en la doc — linkeá al archivo.
2. **Si lo cambiás en el código, abrí la doc en el mismo commit.**
3. **Si la doc miente, es peor que no tener doc.** Borrá lo que ya no aplica.
4. **Las fechas se ponen explícitas**: "última actualización: 2026-05-11" arriba de los docs que cambian seguido.
5. **Evitá copy-paste de comandos sin testear.** Probá cada comando que pongas.

## 12. Convenciones de estilo

- Markdown estándar (CommonMark). Sin extensiones rebuscadas.
- Bloques de código con lenguaje declarado (` ```bash`, ` ```sql`, ` ```python `).
- Tablas para enumeraciones técnicas (puertos, variables, errores).
- Listas para pasos imperativos.
- Negrita para conceptos clave que el lector necesita recordar.
- Sin emojis en docs técnicos.

---

**Próximo paso:** [15_CHECKLIST_DIARIO.md](15_CHECKLIST_DIARIO.md) — el checklist que abrís cada día.
