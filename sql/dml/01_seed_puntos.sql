-- =============================================================================
-- SINIA-UY — Seed: Puntos de Monitoreo (Uruguay + Brasil + Argentina)
-- =============================================================================
-- 11 ciudades en 3 países: Uruguay (sede), Brasil y Argentina (limítrofes
-- con mayor influencia sobre incendios e impacto atmosférico en Uruguay).
-- Período analítico: 2018-2025.
-- Idempotente: usa INSERT ... ON CONFLICT DO NOTHING.
-- =============================================================================

INSERT INTO puntos_monitoreo (nombre, pais, region, latitud, longitud, activo)
VALUES
    -- ── Brasil (5 puntos — fuente principal de humo transfronterizo) ────────
    ('Cuiabá',       'BRA', 'Mato Grosso — corazón del Cerrado',           -15.60, -56.10, TRUE),
    ('Porto_Alegre', 'BRA', 'Rio Grande do Sul — frontera sur',            -30.03, -51.23, TRUE),
    ('Manaus',       'BRA', 'Amazonas — amazonia occidental',               -3.10, -60.02, TRUE),
    ('Campo_Grande', 'BRA', 'Mato Grosso do Sul — Pantanal',               -20.47, -54.62, TRUE),
    ('Brasília',     'BRA', 'Distrito Federal — Cerrado central',          -15.78, -47.93, TRUE),
    -- ── Argentina (4 puntos — norte y centro, frontera con Uruguay) ─────────
    ('Salta',        'ARG', 'NOA — yungas y chaco salteño',                -24.79, -65.41, TRUE),
    ('Posadas',      'ARG', 'Misiones — selva misionera limítrofe',        -27.37, -55.90, TRUE),
    ('Buenos_Aires', 'ARG', 'AMBA — frontera oeste con Uruguay',           -34.61, -58.37, TRUE),
    ('Mendoza',      'ARG', 'Cuyo — incendios de interfaz urbano-forestal',-32.89, -68.85, TRUE),
    -- ── Uruguay (2 puntos — sede del proyecto y capital) ────────────────────
    ('Rivera',       'URY', 'Rivera — sede UTEC, frontera con Brasil',     -30.91, -55.55, TRUE),
    ('Montevideo',   'URY', 'Montevideo — capital, referencia sur',        -34.90, -56.19, TRUE)
ON CONFLICT (nombre) DO NOTHING;

-- Verificación
SELECT id, nombre, pais, latitud, longitud
FROM puntos_monitoreo
ORDER BY pais, nombre;
