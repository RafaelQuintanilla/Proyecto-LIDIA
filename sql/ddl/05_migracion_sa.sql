-- =============================================================================
-- SINIA-SA — Script de Migración (Uruguay → Sudamérica)
-- =============================================================================
-- Este script modifica la base de datos EXISTENTE para ampliar el alcance
-- geográfico de Uruguay (5 puntos) a Sudamérica (18 puntos, 6 países).
--
-- IMPORTANTE: Ejecutar SOLO UNA VEZ sobre la base existente sinia_uy.
-- Es idempotente: usa IF EXISTS / IF NOT EXISTS para no fallar si ya fue aplicado.
--
-- Ejecutar con:
--   psql -U postgres -d sinia_uy -f sql/ddl/05_migracion_sa.sql
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- PASO 1: Eliminar los CHECK constraints de Uruguay en puntos_monitoreo
-- ---------------------------------------------------------------------------
-- Los nombres de constraints se encuentran con:
-- SELECT conname FROM pg_constraint WHERE conrelid = 'puntos_monitoreo'::regclass;

DO $$
DECLARE
    c RECORD;
BEGIN
    -- Eliminar todos los CHECK constraints en latitud/longitud de puntos_monitoreo
    FOR c IN
        SELECT conname
        FROM pg_constraint
        WHERE conrelid = 'puntos_monitoreo'::regclass
          AND contype = 'c'
          AND (
              pg_get_constraintdef(oid) LIKE '%latitud%'
              OR pg_get_constraintdef(oid) LIKE '%longitud%'
          )
    LOOP
        EXECUTE format('ALTER TABLE puntos_monitoreo DROP CONSTRAINT IF EXISTS %I', c.conname);
        RAISE NOTICE 'Eliminado constraint: %', c.conname;
    END LOOP;
END;
$$;

-- Agregar CHECK con rango Sudamérica
ALTER TABLE puntos_monitoreo
    ADD CONSTRAINT puntos_latitud_sa  CHECK (latitud  BETWEEN -90.0 AND 90.0),
    ADD CONSTRAINT puntos_longitud_sa CHECK (longitud BETWEEN -180.0 AND 180.0);

-- ---------------------------------------------------------------------------
-- PASO 2: Agregar columna pais a puntos_monitoreo
-- ---------------------------------------------------------------------------
ALTER TABLE puntos_monitoreo
    ADD COLUMN IF NOT EXISTS pais    CHAR(3) DEFAULT 'URY',
    ADD COLUMN IF NOT EXISTS region  VARCHAR(80);

-- Rellenar pais para los 5 puntos Uruguay existentes
UPDATE puntos_monitoreo SET pais = 'URY' WHERE pais IS NULL;

COMMENT ON COLUMN puntos_monitoreo.pais   IS 'Código ISO 3166-1 alpha-3 del país';
COMMENT ON COLUMN puntos_monitoreo.region IS 'Descripción de la zona de monitoreo';

-- ---------------------------------------------------------------------------
-- PASO 3: Eliminar los CHECK constraints de Uruguay en focos_calor
-- ---------------------------------------------------------------------------

DO $$
DECLARE
    c RECORD;
BEGIN
    FOR c IN
        SELECT conname
        FROM pg_constraint
        WHERE conrelid = 'focos_calor'::regclass
          AND contype = 'c'
          AND (
              pg_get_constraintdef(oid) LIKE '%latitud%'
              OR pg_get_constraintdef(oid) LIKE '%longitud%'
          )
    LOOP
        EXECUTE format('ALTER TABLE focos_calor DROP CONSTRAINT IF EXISTS %I', c.conname);
        RAISE NOTICE 'Eliminado constraint: %', c.conname;
    END LOOP;
END;
$$;

-- Agregar CHECK con rango global
ALTER TABLE focos_calor
    ADD CONSTRAINT focos_latitud_global  CHECK (latitud  BETWEEN -90.0 AND 90.0),
    ADD CONSTRAINT focos_longitud_global CHECK (longitud BETWEEN -180.0 AND 180.0);

-- ---------------------------------------------------------------------------
-- PASO 4: Agregar columna pais a focos_calor
-- ---------------------------------------------------------------------------
ALTER TABLE focos_calor
    ADD COLUMN IF NOT EXISTS pais CHAR(3) DEFAULT 'URY';

-- Los focos existentes (688) son de Uruguay — marcamos URY
UPDATE focos_calor SET pais = 'URY' WHERE pais IS NULL;

COMMENT ON COLUMN focos_calor.pais IS 'Código ISO 3166-1 alpha-3 asignado por bbox en la transformación';

-- ---------------------------------------------------------------------------
-- PASO 5: Crear tabla paises_referencia (si no existe)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS paises_referencia (
    codigo_iso3  CHAR(3)      PRIMARY KEY,
    codigo_iso2  CHAR(2)      NOT NULL UNIQUE,
    nombre       VARCHAR(80)  NOT NULL,
    region       VARCHAR(50)  DEFAULT 'Sudamérica',
    activo       BOOLEAN      NOT NULL DEFAULT TRUE
);

INSERT INTO paises_referencia (codigo_iso3, codigo_iso2, nombre) VALUES
    ('BRA', 'BR', 'Brasil'),
    ('BOL', 'BO', 'Bolivia'),
    ('PRY', 'PY', 'Paraguay'),
    ('ARG', 'AR', 'Argentina'),
    ('CHL', 'CL', 'Chile'),
    ('PER', 'PE', 'Perú'),
    ('URY', 'UY', 'Uruguay')       -- Incluimos Uruguay para compatibilidad con datos históricos
ON CONFLICT (codigo_iso3) DO NOTHING;

-- ---------------------------------------------------------------------------
-- PASO 6: Crear tabla precipitacion_mensual (si no existe)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS precipitacion_mensual (
    id               SERIAL       PRIMARY KEY,
    anio             SMALLINT     NOT NULL CHECK (anio BETWEEN 1981 AND 2100),
    mes              SMALLINT     NOT NULL CHECK (mes  BETWEEN 1 AND 12),
    id_punto         INTEGER      NOT NULL
                         REFERENCES puntos_monitoreo(id) ON DELETE RESTRICT,
    precipitacion_mm NUMERIC(8,2) CHECK (precipitacion_mm >= 0),
    fuente           VARCHAR(30)  NOT NULL DEFAULT 'CHIRPS_ClimateSERV',
    insertado_en     TIMESTAMP    NOT NULL DEFAULT NOW(),
    UNIQUE (anio, mes, id_punto)
);

COMMENT ON TABLE precipitacion_mensual IS 'Precipitación total mensual en mm — CHIRPS (UCSB/NASA)';

-- ---------------------------------------------------------------------------
-- PASO 7: Crear tabla cobertura_vegetal (si no existe)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cobertura_vegetal (
    id               SERIAL      PRIMARY KEY,
    anio             SMALLINT    NOT NULL CHECK (anio BETWEEN 2001 AND 2100),
    id_punto         INTEGER     NOT NULL
                         REFERENCES puntos_monitoreo(id) ON DELETE RESTRICT,
    lc_type1         SMALLINT    CHECK (lc_type1 BETWEEN 1 AND 255),
    lc_descripcion   VARCHAR(60),
    fuente           VARCHAR(30) NOT NULL DEFAULT 'MODIS_MCD12Q1_AppEEARS',
    insertado_en     TIMESTAMP   NOT NULL DEFAULT NOW(),
    UNIQUE (anio, id_punto)
);

COMMENT ON TABLE cobertura_vegetal IS 'Tipo de cobertura/uso del suelo anual MODIS MCD12Q1 v6.1';

-- ---------------------------------------------------------------------------
-- PASO 8: Índices para las nuevas tablas y columnas
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_focos_pais          ON focos_calor(pais);
CREATE INDEX IF NOT EXISTS idx_focos_pais_fecha    ON focos_calor(pais, fecha_adq);
CREATE INDEX IF NOT EXISTS idx_precip_punto_anio   ON precipitacion_mensual(id_punto, anio, mes);
CREATE INDEX IF NOT EXISTS idx_precip_pais_anio    ON precipitacion_mensual(anio, mes);
CREATE INDEX IF NOT EXISTS idx_cobertura_punto_anio ON cobertura_vegetal(id_punto, anio);

-- ---------------------------------------------------------------------------
-- VERIFICACIÓN FINAL
-- ---------------------------------------------------------------------------
DO $$
DECLARE
    n_tablas INTEGER;
BEGIN
    SELECT COUNT(*) INTO n_tablas
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_name IN (
          'puntos_monitoreo', 'focos_calor', 'meteo_diario',
          'calidad_aire_diario', 'etl_ejecuciones',
          'paises_referencia', 'precipitacion_mensual', 'cobertura_vegetal'
      );
    RAISE NOTICE 'Migración SA completada. Tablas activas: %/8', n_tablas;
END;
$$;

COMMIT;
