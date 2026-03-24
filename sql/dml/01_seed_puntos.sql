-- =============================================================================
-- SINIA-SA — Seed: Puntos de Monitoreo (Sudamérica)
-- =============================================================================
-- 18 ciudades en 6 países núcleo seleccionadas por relevancia histórica
-- en actividad de incendios forestales (2018-2025).
-- Idempotente: usa INSERT ... ON CONFLICT DO NOTHING.
-- =============================================================================

INSERT INTO puntos_monitoreo (nombre, pais, region, latitud, longitud, activo)
VALUES
    -- ── Brasil (5 puntos) ────────────────────────────────────────────────────
    ('Cuiabá',       'BRA', 'Mato Grosso — corazón del Cerrado',          -15.60, -56.10, TRUE),
    ('Porto_Alegre', 'BRA', 'Rio Grande do Sul — frontera sur',           -30.03, -51.23, TRUE),
    ('Manaus',       'BRA', 'Amazonas — amazonia occidental',              -3.10, -60.02, TRUE),
    ('Campo_Grande', 'BRA', 'Mato Grosso do Sul — Pantanal',             -20.47, -54.62, TRUE),
    ('Brasília',     'BRA', 'Distrito Federal — Cerrado central',         -15.78, -47.93, TRUE),
    -- ── Bolivia (3 puntos) ──────────────────────────────────────────────────
    ('Santa_Cruz',   'BOL', 'Santa Cruz — Chiquitanía, zona crítica',     -17.80, -63.17, TRUE),
    ('Trinidad',     'BOL', 'Beni — amazonia boliviana',                  -14.83, -64.90, TRUE),
    ('La_Paz',       'BOL', 'La Paz — capital administrativa',            -16.50, -68.15, TRUE),
    -- ── Paraguay (2 puntos) ─────────────────────────────────────────────────
    ('Asunción',     'PRY', 'Capital — corredor central de incendios',    -25.29, -57.64, TRUE),
    ('Concepción',   'PRY', 'Concepción — Chaco paraguayo norte',         -23.41, -57.43, TRUE),
    -- ── Argentina (4 puntos) ────────────────────────────────────────────────
    ('Salta',        'ARG', 'NOA — yungas y chaco salteño',               -24.79, -65.41, TRUE),
    ('Posadas',      'ARG', 'Misiones — selva misionera',                 -27.37, -55.90, TRUE),
    ('Buenos_Aires', 'ARG', 'AMBA — referencia sur del sistema',          -34.61, -58.37, TRUE),
    ('Mendoza',      'ARG', 'Cuyo — incendios de interfaz urbano-forestal',-32.89, -68.85, TRUE),
    -- ── Chile (2 puntos) ────────────────────────────────────────────────────
    ('Santiago',     'CHL', 'Región Metropolitana — zona de interfaz',    -33.46, -70.65, TRUE),
    ('Temuco',       'CHL', 'La Araucanía — zona forestal crítica',       -38.74, -72.59, TRUE),
    -- ── Perú (2 puntos) ─────────────────────────────────────────────────────
    ('Lima',         'PER', 'Capital costera — referencia occidental',    -12.06, -77.04, TRUE),
    ('Cusco',        'PER', 'Sur andino — colindante con amazonia',       -13.53, -71.97, TRUE)
ON CONFLICT (nombre) DO NOTHING;

-- Verificación
SELECT id, nombre, pais, latitud, longitud
FROM puntos_monitoreo
ORDER BY pais, nombre;
