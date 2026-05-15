# Revision y sincronizacion UTEC - 2026-05-15

## Objetivo

Verificar si las bases de datos del servidor UTEC estaban actualizadas y sincronizar los datos operativos recientes del sistema SINIA-UY.

## Estado inicial encontrado

Antes de la sincronizacion, PostgreSQL UTEC estaba accesible, pero los datos operativos no estaban al dia:

- `focos_calor`: ultimo dato historico en `2024-12-31`.
- `meteo_diario` forecast actual: `0` filas desde la fecha corriente.
- `calidad_aire_diario`: ultimo dato en `2026-03-29`.
- MongoDB tenia snapshots historicos, pero no snapshots NRT de mayo 2026.

## Acciones ejecutadas

Se realizo una sincronizacion controlada contra UTEC, sin eliminar tablas ni tocar tablas ajenas al proyecto como `clientes`, `productos` o `ventas`.

Datos cargados en PostgreSQL UTEC:

- `forecast_riesgo.parquet`: `77` filas de pronostico, desde `2026-05-15` hasta `2026-05-21`.
- `cams_nrt_procesado.parquet`: `828` filas procesadas; `517` insertadas y `311` ya existentes.
- `firms_nrt_procesado.parquet`: `5283` focos NRT insertados, desde `2026-05-11` hasta `2026-05-15`.

Datos cargados en MongoDB UTEC:

- `5` snapshots diarios NRT en `focos_snapshots`.
- `5283` focos embebidos en snapshots.
- `1` registro nuevo en `ejecuciones_etl` para la carga Mongo NRT.

## Verificacion final UTEC

PostgreSQL UTEC:

| Control | Resultado |
|---|---:|
| `focos_calor` total | `3836386` |
| `focos_calor` rango total | `2024-01-01` a `2026-05-15` |
| focos NRT ultimos 5 dias | `5283` |
| rango focos NRT | `2026-05-11` a `2026-05-15` |
| focos ultimas 24 horas | `303` |
| forecast vigente | `77` |
| rango forecast | `2026-05-15` a `2026-05-21` |
| CAMS ultimos 5 dias | `66` |
| rango CAMS reciente | `2026-05-10` a `2026-05-15` |
| `etl_ejecuciones` | `34` |
| ultima finalizacion ETL PostgreSQL | `2026-05-15 13:48:11 UTC` |

MongoDB UTEC:

| Control | Resultado |
|---|---:|
| colecciones | `alertas`, `ejecuciones_etl`, `eventos`, `focos_snapshots` |
| `focos_snapshots` | `352` |
| `ejecuciones_etl` | `2` |
| `alertas` | `0` |
| `eventos` | `2` |
| ultimo snapshot | `2026-05-15` |
| focos en ultimo snapshot | `303` |
| ultima ejecucion Mongo | `firms_nrt/load_mongo`, estado `ok` |

## Actualizacion de permisos MongoDB

Luego de solicitar el permiso al encargado del servidor, se verifico que el
usuario `grp03` ya puede ejecutar `collMod` sobre `grp03db`.

Resultado de la verificacion:

| Coleccion | Validador JSON Schema | Indices verificados |
|---|---|---|
| `ejecuciones_etl` | aplicado | `_id_`, `idx_estado`, `idx_fuente_inicio` |
| `alertas` | aplicado | `_id_`, `idx_activas`, `idx_fecha_gen`, `idx_tipo_nivel` |
| `focos_snapshots` | aplicado | `_id_`, `idx_fecha_unico` |

Conteos al momento de la verificacion:

| Coleccion | Documentos |
|---|---:|
| `ejecuciones_etl` | `2` |
| `alertas` | `0` |
| `focos_snapshots` | `352` |

## Observaciones

- Las bases del servidor UTEC quedaron actualizadas con datos operativos recientes al `2026-05-15`.
- MongoDB UTEC ya permite actualizar validadores JSON Schema con `collMod`.
- La sincronizacion realizada fue incremental y segura. No se recargo el historico completo para evitar una operacion pesada sobre una base compartida.

## Conclusion

El sistema local esta operativo en tiempo real y las bases UTEC quedaron sincronizadas con los datos recientes necesarios para el dashboard y las consultas operativas.
