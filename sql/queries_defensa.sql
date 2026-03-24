-- =============================================================================
-- SINIA-SA — Queries analíticas para la defensa del proyecto
-- =============================================================================
-- Pregunta central: ¿cuándo, dónde y por qué ocurren incendios en Sudamérica?
-- Período: 2018-2024 | 6 países | 18 puntos de monitoreo
-- =============================================================================


-- =============================================================================
-- BLOQUE 1: VISIÓN GENERAL DEL DATASET
-- "¿Qué tan grande es el sistema que construimos?"
-- =============================================================================

-- 1.1 Resumen general del sistema
SELECT
    'focos_calor'            AS tabla,
    COUNT(*)                 AS registros,
    MIN(fecha_adq)           AS desde,
    MAX(fecha_adq)           AS hasta
FROM focos_calor
UNION ALL
SELECT 'meteo_diario',       COUNT(*), MIN(fecha)::date, MAX(fecha)::date FROM meteo_diario
UNION ALL
SELECT 'calidad_aire_diario',COUNT(*), MIN(fecha)::date, MAX(fecha)::date FROM calidad_aire_diario
UNION ALL
SELECT 'precipitacion_mensual',COUNT(*), MIN(fecha)::date, MAX(fecha)::date FROM precipitacion_mensual
UNION ALL
SELECT 'cobertura_vegetal',  COUNT(*), NULL, NULL FROM cobertura_vegetal
ORDER BY 1;


-- 1.2 Focos por país (ranking total 2018-2024)
SELECT
    pais,
    COUNT(*)                             AS total_focos,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS porcentaje,
    ROUND(AVG(potencia_radiativa), 1)    AS frp_promedio_mw,
    ROUND(MAX(potencia_radiativa), 1)    AS frp_maximo_mw,
    COUNT(DISTINCT fecha_adq)            AS dias_con_focos
FROM focos_calor
WHERE pais IS NOT NULL
GROUP BY pais
ORDER BY total_focos DESC;


-- =============================================================================
-- BLOQUE 2: PATRONES TEMPORALES
-- "¿CUÁNDO ocurren los incendios?"
-- =============================================================================

-- 2.1 Estacionalidad mensual — promedio de focos por mes del año (todos los países)
SELECT
    TO_CHAR(TO_DATE(mes_num::text, 'MM'), 'Month') AS mes,
    mes_num,
    ROUND(AVG(focos_mes))                           AS promedio_focos,
    MAX(focos_mes)                                  AS maximo_historico,
    MIN(focos_mes)                                  AS minimo_historico
FROM (
    SELECT
        EXTRACT(MONTH FROM fecha_adq) AS mes_num,
        EXTRACT(YEAR  FROM fecha_adq) AS anio,
        COUNT(*)                       AS focos_mes
    FROM focos_calor
    GROUP BY 1, 2
) sub
GROUP BY mes_num
ORDER BY mes_num;


-- 2.2 Ranking de años por actividad total
SELECT
    EXTRACT(YEAR FROM fecha_adq)::int    AS anio,
    COUNT(*)                             AS total_focos,
    ROUND(AVG(potencia_radiativa), 1)    AS frp_promedio,
    COUNT(DISTINCT fecha_adq)            AS dias_activos,
    COUNT(DISTINCT pais)                 AS paises_afectados
FROM focos_calor
GROUP BY 1
ORDER BY total_focos DESC;


-- 2.3 Top 10 días con más focos en toda la historia
SELECT
    fecha_adq,
    TO_CHAR(fecha_adq, 'Day DD Mon YYYY') AS fecha_texto,
    COUNT(*)                              AS focos_del_dia,
    ROUND(AVG(potencia_radiativa), 1)     AS frp_promedio,
    ROUND(MAX(potencia_radiativa), 1)     AS frp_maximo,
    STRING_AGG(DISTINCT pais, ', ' ORDER BY pais) AS paises
FROM focos_calor
GROUP BY fecha_adq
ORDER BY focos_del_dia DESC
LIMIT 10;


-- 2.4 Focos diurnos vs nocturnos por país
SELECT
    pais,
    SUM(CASE WHEN es_diurno THEN 1 ELSE 0 END)      AS focos_diurnos,
    SUM(CASE WHEN NOT es_diurno THEN 1 ELSE 0 END)  AS focos_nocturnos,
    ROUND(
        SUM(CASE WHEN es_diurno THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1
    )                                                AS pct_diurno
FROM focos_calor
WHERE pais IS NOT NULL
GROUP BY pais
ORDER BY focos_diurnos + focos_nocturnos DESC;


-- =============================================================================
-- BLOQUE 3: DISTRIBUCIÓN GEOGRÁFICA
-- "¿DÓNDE ocurren los incendios?"
-- =============================================================================

-- 3.1 Focos por país y año (tabla cruzada de actividad)
SELECT
    pais,
    SUM(CASE WHEN anio = 2018 THEN focos ELSE 0 END) AS "2018",
    SUM(CASE WHEN anio = 2019 THEN focos ELSE 0 END) AS "2019",
    SUM(CASE WHEN anio = 2020 THEN focos ELSE 0 END) AS "2020",
    SUM(CASE WHEN anio = 2021 THEN focos ELSE 0 END) AS "2021",
    SUM(CASE WHEN anio = 2022 THEN focos ELSE 0 END) AS "2022",
    SUM(CASE WHEN anio = 2023 THEN focos ELSE 0 END) AS "2023",
    SUM(focos)                                        AS total
FROM (
    SELECT
        pais,
        EXTRACT(YEAR FROM fecha_adq)::int AS anio,
        COUNT(*) AS focos
    FROM focos_calor
    WHERE pais IS NOT NULL
    GROUP BY pais, anio
) t
GROUP BY pais
ORDER BY total DESC;


-- 3.2 Intensidad por país — FRP máximo histórico (los incendios más grandes)
SELECT
    pais,
    ROUND(MAX(potencia_radiativa), 1)  AS frp_maximo_historico_mw,
    ROUND(AVG(potencia_radiativa), 1)  AS frp_promedio_mw,
    COUNT(*) FILTER (WHERE potencia_radiativa > 1000) AS focos_extremos_gt1000mw
FROM focos_calor
WHERE pais IS NOT NULL AND potencia_radiativa IS NOT NULL
GROUP BY pais
ORDER BY frp_maximo_historico_mw DESC;


-- =============================================================================
-- BLOQUE 4: CORRELACIÓN RIESGO METEOROLÓGICO ↔ FOCOS
-- "¿POR QUÉ ocurren los incendios?"
-- =============================================================================

-- 4.1 Índice de riesgo promedio por punto (ranking de zonas más vulnerables)
SELECT
    punto,
    ROUND(AVG(indice_riesgo), 3)       AS indice_promedio,
    ROUND(MAX(indice_riesgo), 3)       AS indice_maximo,
    COUNT(*) FILTER (
        WHERE nivel_riesgo IN ('alto', 'muy_alto')
    )                                  AS dias_alto_riesgo,
    COUNT(*)                           AS total_dias,
    ROUND(
        COUNT(*) FILTER (WHERE nivel_riesgo IN ('alto', 'muy_alto')) * 100.0
        / COUNT(*), 1
    )                                  AS pct_dias_alto_riesgo
FROM meteo_diario
WHERE tipo_dato = 'historico'
GROUP BY punto
ORDER BY indice_promedio DESC;


-- 4.2 ¿Los días de alto riesgo coinciden con más focos? (correlación visual)
-- Une meteo con focos del mismo día para cada punto SA
WITH riesgo_diario AS (
    SELECT
        fecha::date,
        AVG(indice_riesgo)  AS riesgo_promedio,
        MAX(nivel_riesgo)   AS nivel_maximo
    FROM meteo_diario
    WHERE tipo_dato = 'historico'
    GROUP BY fecha::date
),
focos_diarios AS (
    SELECT fecha_adq, COUNT(*) AS focos
    FROM focos_calor
    GROUP BY fecha_adq
)
SELECT
    r.nivel_maximo,
    COUNT(*)                        AS dias,
    ROUND(AVG(f.focos))             AS focos_promedio_dia,
    ROUND(MAX(f.focos))             AS focos_maximo_dia,
    ROUND(AVG(r.riesgo_promedio),3) AS indice_riesgo_promedio
FROM riesgo_diario r
LEFT JOIN focos_diarios f ON f.fecha_adq = r.fecha
GROUP BY r.nivel_maximo
ORDER BY focos_promedio_dia DESC;


-- 4.3 Precipitación vs actividad de fuego (¿la lluvia baja los focos?)
SELECT
    pm.punto,
    pm.fecha,
    pm.precipitacion_mm,
    COALESCE(
        (SELECT COUNT(*) FROM focos_calor fc
         WHERE EXTRACT(YEAR FROM fc.fecha_adq)  = EXTRACT(YEAR FROM pm.fecha)
           AND EXTRACT(MONTH FROM fc.fecha_adq) = EXTRACT(MONTH FROM pm.fecha)
        ), 0
    )                              AS focos_ese_mes
FROM precipitacion_mensual pm
ORDER BY pm.fecha, pm.punto
LIMIT 50;


-- =============================================================================
-- BLOQUE 5: CALIDAD DEL AIRE — IMPACTO EN LA POBLACIÓN
-- "¿Los incendios afectaron la salud de la gente?"
-- =============================================================================

-- 5.1 Días que superaron el límite OMS de PM10 (45 µg/m³) por punto
SELECT
    p.nombre                           AS punto,
    COUNT(*) FILTER (WHERE c.supera_oms_pm10) AS dias_sobre_limite_oms,
    COUNT(*)                           AS total_dias,
    ROUND(AVG(c.pm10_media), 1)        AS pm10_promedio,
    ROUND(MAX(c.pm10_max), 1)          AS pm10_maximo,
    ROUND(AVG(c.european_aqi_media))   AS aqi_promedio
FROM calidad_aire_diario c
JOIN puntos_monitoreo p ON p.id = c.id_punto
GROUP BY p.nombre
ORDER BY dias_sobre_limite_oms DESC;


-- 5.2 Peores meses de calidad del aire (2022-2023)
SELECT
    DATE_TRUNC('month', fecha)::date AS mes,
    COUNT(*) FILTER (WHERE supera_oms_pm10) AS puntos_dias_sobre_oms,
    ROUND(AVG(pm10_media), 1)        AS pm10_promedio_region,
    ROUND(MAX(pm10_max), 1)          AS pm10_maximo_region
FROM calidad_aire_diario
GROUP BY 1
ORDER BY pm10_promedio_region DESC
LIMIT 12;


-- =============================================================================
-- BLOQUE 6: COBERTURA VEGETAL — COMBUSTIBLE POTENCIAL
-- "¿Qué tipo de vegetación quema más?"
-- =============================================================================

-- 6.1 Cobertura vegetal por punto y año
SELECT
    p.nombre             AS punto,
    p.pais               AS pais,
    cv.anio,
    cv.clase_lc          AS tipo_cobertura,
    cv.descripcion_lc    AS descripcion
FROM cobertura_vegetal cv
JOIN puntos_monitoreo p ON p.id = cv.id_punto
ORDER BY p.pais, p.nombre, cv.anio;


-- =============================================================================
-- BLOQUE 7: MÉTRICAS DEL PIPELINE ETL
-- "¿Cómo funciona la ingeniería de datos detrás del sistema?"
-- =============================================================================

-- 7.1 Audit trail del ETL — cuántas ejecuciones y cuántos datos cargados
SELECT
    fuente,
    tipo_carga,
    COUNT(*)                            AS ejecuciones,
    SUM(filas_procesadas)               AS filas_totales,
    ROUND(AVG(duracion_segundos), 1)    AS duracion_promedio_s,
    MAX(fin_en)                         AS ultima_ejecucion
FROM etl_ejecuciones
GROUP BY fuente, tipo_carga
ORDER BY fuente, tipo_carga;


-- 7.2 Tiempos de respuesta de las consultas clave (benchmark para la defensa)
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT * FROM v_focos_por_pais_mes;

EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT * FROM v_riesgo_actual;

EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT COUNT(*), AVG(potencia_radiativa) FROM focos_calor WHERE pais = 'BRA';
