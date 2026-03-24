-- =============================================================================
-- SINIA-UY — Consultas Analíticas
-- =============================================================================
-- 10 preguntas analíticas del proyecto respondidas con SQL.
-- Cada consulta incluye su pregunta, la consulta y la interpretación esperada.
-- =============================================================================

-- Q1: ¿Cuántos focos de calor se detectaron por mes?
-- Responde: evolución temporal de la actividad de incendios en Uruguay.
SELECT
    DATE_TRUNC('month', fecha_adq) AS mes,
    COUNT(*)                        AS total_focos,
    ROUND(AVG(potencia_radiativa)::NUMERIC, 2) AS frp_promedio_mw
FROM focos_calor
GROUP BY DATE_TRUNC('month', fecha_adq)
ORDER BY mes DESC;

-- Q2: ¿Cuál es el ranking de días con mayor cantidad de focos?
-- Responde: identificación de días críticos para retroalimentar alertas tempranas.
SELECT
    fecha_adq,
    COUNT(*)                   AS focos,
    MAX(potencia_radiativa)    AS frp_max_mw,
    COUNT(CASE WHEN confianza_num = 3 THEN 1 END) AS focos_alta_confianza
FROM focos_calor
GROUP BY fecha_adq
ORDER BY focos DESC
LIMIT 15;

-- Q3: ¿Cuántos días en nivel de riesgo ALTO o MUY ALTO tuvo cada departamento?
-- Responde: priorización territorial de vigilancia preventiva.
SELECT
    p.nombre AS punto,
    COUNT(*) FILTER (WHERE m.nivel_riesgo = 'alto')     AS dias_alto,
    COUNT(*) FILTER (WHERE m.nivel_riesgo = 'muy_alto') AS dias_muy_alto,
    COUNT(*) FILTER (WHERE m.nivel_riesgo IN ('alto','muy_alto')) AS dias_criticos_total,
    ROUND(AVG(m.indice_riesgo)::NUMERIC, 4)              AS indice_promedio
FROM meteo_diario m
JOIN puntos_monitoreo p ON p.id = m.id_punto
WHERE m.tipo_dato = 'historico'
GROUP BY p.nombre
ORDER BY dias_criticos_total DESC;

-- Q4: ¿Cómo evoluciona el índice de riesgo mensual por punto? (agregación temporal)
-- Responde: patrón estacional del riesgo de incendio en Uruguay.
SELECT
    p.nombre                             AS punto,
    DATE_TRUNC('month', m.fecha)         AS mes,
    ROUND(AVG(m.indice_riesgo)::NUMERIC, 4)  AS riesgo_promedio,
    ROUND(MAX(m.indice_riesgo)::NUMERIC, 4)  AS riesgo_maximo,
    COUNT(*) FILTER (WHERE m.nivel_riesgo IN ('alto','muy_alto')) AS dias_criticos
FROM meteo_diario m
JOIN puntos_monitoreo p ON p.id = m.id_punto
WHERE m.tipo_dato = 'historico'
GROUP BY p.nombre, DATE_TRUNC('month', m.fecha)
ORDER BY p.nombre, mes;

-- Q5: ¿Hay correlación entre días de alto riesgo meteorológico y focos detectados?
-- Responde: validación del índice de riesgo comparándolo con focos reales.
SELECT
    m.fecha,
    p.nombre                       AS punto,
    m.nivel_riesgo,
    ROUND(m.indice_riesgo::NUMERIC, 4) AS indice_riesgo,
    f.focos_en_radio               AS focos_detectados
FROM meteo_diario m
JOIN puntos_monitoreo p ON p.id = m.id_punto
LEFT JOIN (
    SELECT
        fecha_adq,
        COUNT(*) AS focos_en_radio
    FROM focos_calor
    GROUP BY fecha_adq
) f ON f.fecha_adq = m.fecha
WHERE m.tipo_dato = 'historico'
  AND m.nivel_riesgo IN ('alto', 'muy_alto')
ORDER BY m.indice_riesgo DESC
LIMIT 30;

-- Q6: ¿Cuántos días superó Uruguay el límite OMS de PM10 (45 µg/m³)?
-- Responde: impacto en salud pública de incendios y contaminación ambiental.
SELECT
    p.nombre                              AS punto,
    COUNT(*) FILTER (WHERE c.supera_oms_pm10) AS dias_sobre_limite_oms,
    ROUND(AVG(c.pm10_media)::NUMERIC, 2)     AS pm10_promedio,
    ROUND(MAX(c.pm10_media)::NUMERIC, 2)     AS pm10_maximo,
    COUNT(*)                              AS total_dias_registrados
FROM calidad_aire_diario c
JOIN puntos_monitoreo p ON p.id = c.id_punto
GROUP BY p.nombre
ORDER BY dias_sobre_limite_oms DESC;

-- Q7: ¿Cuál es el pronóstico de riesgo para los próximos 7 días? (comparación entre puntos)
-- Responde: apoyo a decisiones de asignación de recursos preventivos.
SELECT
    p.nombre         AS punto,
    m.fecha,
    m.indice_riesgo,
    m.nivel_riesgo,
    m.temperature_2m_max,
    m.relative_humidity_2m_min,
    m.wind_speed_10m_max
FROM meteo_diario m
JOIN puntos_monitoreo p ON p.id = m.id_punto
WHERE m.tipo_dato = 'forecast'
  AND m.fecha >= CURRENT_DATE
ORDER BY m.indice_riesgo DESC, m.fecha;

-- Q8: ¿Cuál es el mes con mayor riesgo histórico acumulado? (análisis estacional)
-- Responde: identificación de períodos críticos para planificación preventiva.
SELECT
    EXTRACT(MONTH FROM m.fecha) AS mes_numero,
    TO_CHAR(m.fecha, 'Month')   AS mes_nombre,
    ROUND(AVG(m.indice_riesgo)::NUMERIC, 4)  AS riesgo_promedio,
    COUNT(*) FILTER (WHERE m.nivel_riesgo IN ('alto','muy_alto')) AS dias_criticos
FROM meteo_diario m
WHERE m.tipo_dato = 'historico'
  AND m.indice_riesgo IS NOT NULL
GROUP BY EXTRACT(MONTH FROM m.fecha), TO_CHAR(m.fecha, 'Month')
ORDER BY riesgo_promedio DESC;

-- Q9: ¿En qué horas del día se detectan más focos? (análisis diurno/nocturno)
-- Responde: optimización de ventanas de vigilancia aérea y terrestre.
SELECT
    es_diurno,
    hora_adq_hhmm / 100          AS hora,
    COUNT(*)                     AS focos,
    ROUND(AVG(potencia_radiativa)::NUMERIC, 2) AS frp_promedio
FROM focos_calor
WHERE hora_adq_hhmm IS NOT NULL
GROUP BY es_diurno, hora_adq_hhmm / 100
ORDER BY focos DESC;

-- Q10: ¿Cuáles son los 10 focos más intensos registrados?
-- Responde: identificación de incendios de mayor envergadura para estudio de casos.
SELECT
    fecha_adq,
    latitud,
    longitud,
    potencia_radiativa AS frp_mw,
    confianza_num,
    satelite,
    dia_noche
FROM focos_calor
WHERE confianza_num >= 2   -- Solo confianza nominal o alta
ORDER BY potencia_radiativa DESC NULLS LAST
LIMIT 10;

-- =============================================================================
-- MÉTRICAS DE RENDIMIENTO — para medir impacto de índices
-- =============================================================================
-- Ejecutar con EXPLAIN ANALYZE para comparar antes/después de crear índices:

-- EXPLAIN ANALYZE
-- SELECT * FROM meteo_diario
-- WHERE id_punto = 1 AND tipo_dato = 'historico'
-- ORDER BY fecha DESC LIMIT 90;

-- EXPLAIN ANALYZE
-- SELECT * FROM focos_calor
-- WHERE fecha_adq BETWEEN '2024-01-01' AND '2024-03-31';
