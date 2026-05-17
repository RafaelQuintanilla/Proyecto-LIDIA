# Defensa del dashboard: secciones, datos y propósito

El dashboard de SINIA-UY está hecho en Streamlit y es la capa de explotación
del modelo de datos. No reemplaza a PostgreSQL ni al ETL: consume los datos
procesados y permite mostrar el resultado del pipeline.

Archivo principal:

```text
dashboard/app.py
```

Capa de acceso a datos:

```text
dashboard/db.py
```

La lógica de acceso es:

1. Intentar leer desde PostgreSQL.
2. Si PostgreSQL no está disponible, usar Parquet desde `data/processed/`.

Esto permite defender que el sistema tiene una fuente analítica principal y un
fallback operativo para demo/despliegue.

## Filtros globales

El sidebar tiene filtros que afectan casi todo el dashboard.

### Sección

Permite elegir una página:

- Resumen General
- Focos de Calor
- Índice de Riesgo
- Calidad del Aire
- Análisis de Riesgo
- Comparativo por País
- Tiempo Real
- Fuentes y Datos Crudos

### Período

Obtiene el rango real de focos con `obtener_rango_focos()`.

Desde PostgreSQL:

```sql
SELECT MIN(fecha_adq), MAX(fecha_adq)
FROM focos_calor
WHERE pais IN ('ARG','BRA','URY');
```

Si no hay PostgreSQL, lee `firms_procesado.parquet`.

### País

Permite ver:

- Todos
- Brasil (`BRA`)
- Argentina (`ARG`)
- Uruguay (`URY`)

Este filtro es importante porque demuestra que el modelo usa códigos
normalizados de país.

### Rango de fechas

Permite filtrar dentro del período elegido. Recalcula:

- focos del mapa;
- serie diaria;
- total de focos;
- estadísticas de FRP.

## Sección 1: Resumen General

### Para qué sirve

Es la pantalla ejecutiva. Resume el estado general del sistema y conecta todas
las fuentes: FIRMS, Open-Meteo, CAMS, CHIRPS y MODIS.

### Qué muestra

- Explicación del sistema.
- Fuentes integradas.
- Alertas activas.
- KPIs principales.
- Mapa de focos.
- Evolución semanal.
- Distribución de riesgo.

### Datos que consume

Desde `dashboard/db.py`:

- `cargar_focos()`
- `cargar_focos_por_dia()`
- `contar_focos()`
- `calcular_estadisticas_focos()`
- `cargar_focos_nrt()`
- `cargar_meteo()`
- `cargar_forecast()`
- `cargar_cams()`

### KPIs principales

#### Focos de calor detectados

Sale de `contar_focos()`.

En PostgreSQL:

```sql
SELECT COUNT(*)
FROM focos_calor
WHERE pais IN ('ARG','BRA','URY')
  AND fecha_adq BETWEEN fecha_inicio AND fecha_fin;
```

Defensa:

> Este KPI no usa la muestra del mapa. Usa `COUNT(*)` para mostrar el total
> real del período.

#### FRP máximo registrado

Sale de `calcular_estadisticas_focos()`.

```sql
SELECT MAX(potencia_radiativa)
FROM focos_calor;
```

Defensa:

> FRP significa Fire Radiative Power. Mide intensidad del foco en megawatts.

#### Días de riesgo alto o muy alto

Sale de `meteo`, usando `nivel_riesgo`.

Defensa:

> Este indicador no viene crudo de una API. Es resultado del ETL, que calcula
> el índice de riesgo y lo clasifica.

#### Último nivel de riesgo registrado

Sale del último registro meteorológico disponible.

Defensa:

> Resume el estado más reciente de riesgo según datos históricos procesados.

### Mapa de focos

Puede mostrar:

- focos actuales NRT;
- focos del período seleccionado.

Usa latitud y longitud de FIRMS.

Defensa:

> El mapa demuestra que los datos son georreferenciados. Cada punto proviene
> de una detección satelital.

### Focos por semana

Agrupa la serie diaria en semanas.

Defensa:

> Esto transforma eventos individuales en una lectura temporal para detectar
> picos de actividad.

## Sección 2: Focos de Calor

### Para qué sirve

Analiza específicamente las detecciones satelitales FIRMS.

### Qué muestra

- Mapa de focos.
- Tabla o muestras de focos.
- Distribuciones por fecha, país, confianza o FRP.
- Evolución temporal.

### Datos que consume

Principalmente:

- `focos_calor` en PostgreSQL.
- `firms_procesado.parquet` como fallback.

### Campos importantes

- `fecha_adq`
- `latitud`
- `longitud`
- `pais`
- `potencia_radiativa`
- `confianza_raw`
- `confianza_num`
- `satelite`
- `dia_noche`
- `es_diurno`

### Defensa

> Esta sección muestra los hechos de incendio o anomalía térmica. FIRMS no
> dice necesariamente que cada punto sea un incendio confirmado por bomberos,
> sino una detección satelital de calor con confianza y potencia radiativa.

### Pregunta probable

¿Por qué el mapa no muestra millones de puntos?

Respuesta:

> Por rendimiento visual. El KPI usa el total real, pero el mapa limita o
> muestra una muestra para que la visualización sea navegable.

## Sección 3: Índice de Riesgo

### Para qué sirve

Explica el riesgo calculado a partir de meteorología.

### Qué muestra

- Riesgo por punto.
- Riesgo por fecha.
- Niveles `bajo`, `moderado`, `alto`, `muy_alto`.
- Variables meteorológicas asociadas.

### Datos que consume

- `meteo_diario`
- vista `v_riesgo_historico`
- vista `v_riesgo_actual`
- Parquet `meteo_procesado_*.parquet` como fallback.

### Fórmula

```text
indice_riesgo =
riesgo_temp * 0.25 +
riesgo_humedad * 0.30 +
riesgo_viento * 0.20 +
riesgo_sequia * 0.25
```

### Defensa

> Esta sección muestra una transformación analítica creada por el proyecto.
> Open-Meteo entrega variables meteorológicas crudas; el ETL las normaliza y
> calcula una métrica única entre 0 y 1.

### Pregunta probable

¿El índice viene de Open-Meteo?

Respuesta:

> No. Open-Meteo entrega temperatura, humedad, viento y evapotranspiración.
> El índice es una variable derivada del proyecto.

## Sección 4: Calidad del Aire

### Para qué sirve

Analiza contaminación y partículas asociadas a condiciones ambientales o humo.

### Qué muestra

- PM10.
- PM2.5.
- AQI europeo.
- Días que superan el umbral OMS.
- Nivel de PM10: normal, elevado o alerta.

### Datos que consume

- `calidad_aire_diario`.
- vista `v_alertas_calidad_aire`.
- Parquet `cams_procesado_*.parquet` como fallback.

### Transformación clave

CAMS llega horario. El ETL lo agrupa a diario:

- `pm10_media`
- `pm10_max`
- `pm10_p95`
- `pm2_5_media`
- `pm2_5_max`
- `horas_validas`

### Defensa

> Esta sección demuestra transformación de granularidad: de datos horarios a
> indicadores diarios. Además aplica una regla de negocio: PM10 medio diario
> mayor a 45 µg/m³ supera el umbral OMS.

## Sección 5: Análisis de Riesgo

### Para qué sirve

Cruza riesgo, meteorología y días críticos para entender patrones.

### Qué muestra

- Días críticos.
- Puntos con mayor riesgo.
- Distribución de niveles.
- Variables que explican el riesgo.

### Datos que consume

- `v_dias_criticos`.
- `v_riesgo_historico`.
- `meteo_diario`.

### Defensa

> Esta sección es analítica. No se limita a mostrar datos crudos, sino que
> permite interpretar cuándo y dónde hubo condiciones peligrosas.

### Pregunta probable

¿Qué es un día crítico?

Respuesta:

> Un día crítico es una fecha en la que al menos un punto tuvo `nivel_riesgo`
> alto o muy alto. La vista `v_dias_criticos` agrupa esos casos.

## Sección 6: Comparativo por País

### Para qué sirve

Compara Uruguay, Brasil y Argentina.

### Qué muestra

- Riesgo mensual por país.
- Focos mensuales por país.
- Tabla comparativa.
- Total de focos.
- Riesgo promedio.
- Riesgo máximo.
- Días críticos.
- FRP máximo.

### Datos que consume

- `v_riesgo_por_pais`.
- `v_focos_por_pais_mes`.
- fallback desde Parquet calculado en `dashboard/db.py`.

### Defensa

> Esta sección justifica el alcance regional. Uruguay se analiza junto con
> Brasil y Argentina porque el riesgo ambiental y el humo no respetan fronteras
> administrativas.

### Pregunta probable

¿Por qué comparar países y no solo Uruguay?

Respuesta:

> Porque el sistema estudia riesgo regional. Brasil y Argentina pueden tener
> actividad de focos o condiciones que afectan el contexto ambiental uruguayo.

## Sección 7: Tiempo Real

### Para qué sirve

Muestra información reciente y pronóstico.

### Qué muestra

- Focos NRT de las últimas 24 horas.
- Forecast de riesgo.
- Estado de actualización.
- Alertas si se superan umbrales.

### Datos que consume

- `cargar_focos_nrt()`.
- `cargar_forecast()`.
- `firms_nrt_procesado.parquet`.
- `forecast_riesgo.parquet`.
- vista `v_forecast_riesgo` si existe PostgreSQL.

### Defensa

> Esta sección separa histórico de operación reciente. FIRMS NRT permite ver
> focos cercanos al presente y forecast permite anticipar riesgo futuro.

### Pregunta probable

¿Qué diferencia hay entre histórico y NRT?

Respuesta:

> Histórico es dato consolidado de años anteriores. NRT significa Near Real
> Time: datos recientes con menor latencia.

## Sección 8: Fuentes y Datos Crudos

### Para qué sirve

Demuestra trazabilidad.

### Qué muestra

- Descripción de cada fuente.
- Archivos crudos descargados.
- Columnas originales.
- Muestras de CSV crudo.
- Volumen aproximado de filas.

### Fuentes mostradas

- NASA FIRMS.
- Open-Meteo.
- CAMS.
- CHIRPS.
- MODIS.

### Defensa

> Esta sección es importante para auditoría. Permite demostrar que el dato no
> aparece mágicamente en la base, sino que viene de fuentes externas concretas
> y queda guardado antes de transformarse.

### Pregunta probable

¿Por qué mostrar datos crudos al usuario?

Respuesta:

> No es una pantalla para usuario final común; es una pantalla de evidencia
> técnica. Sirve para defensa, auditoría y trazabilidad del pipeline.

## Estado de base de datos

El sidebar muestra si se está usando:

- PostgreSQL.
- Parquet.

Defensa:

> Esto permite saber si el dashboard está trabajando contra la base analítica
> principal o contra el fallback procesado.

## Auto-refresh

El dashboard tiene opción de auto-refresh cada 5 minutos.

Defensa:

> Es útil para monitoreo operativo, especialmente con datos NRT y forecast.

## Cómo defender el dashboard en una frase

> El dashboard es la capa de visualización y explotación del modelo de datos:
> consume PostgreSQL como fuente principal, usa Parquet como fallback, permite
> filtrar por país y período, muestra focos FIRMS, riesgo meteorológico, calidad
> del aire, comparaciones regionales, tiempo real y evidencia de datos crudos.

## Preguntas trampa

### El dashboard calcula todo?

No. Algunas agregaciones se hacen en vistas SQL o en la capa `dashboard/db.py`.
El dashboard principalmente visualiza y coordina filtros.

### Si PostgreSQL falla, se cae todo?

No. Hay fallback a Parquet para muchas funciones.

### Por qué hay muestras y no todos los focos en mapa?

Por rendimiento visual. El total real se calcula con SQL, pero visualizar
millones de puntos puede volver inutilizable el mapa.

### Qué sección demuestra mejor la base de datos?

Comparativo por País y Análisis de Riesgo, porque usan vistas, agregaciones,
filtros y relaciones entre puntos, países y hechos.

### Qué sección demuestra mejor el ETL?

Fuentes y Datos Crudos, porque permite comparar datos originales con datos
procesados; Índice de Riesgo, porque muestra una variable derivada del ETL.
