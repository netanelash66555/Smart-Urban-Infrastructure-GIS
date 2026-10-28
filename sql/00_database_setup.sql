-- Smart Urban Infrastructure GIS Platform
-- PostgreSQL / PostGIS database setup

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE SCHEMA IF NOT EXISTS gis;

CREATE TABLE IF NOT EXISTS gis.analysis_runs (
    analysis_id BIGSERIAL PRIMARY KEY,
    road_id BIGINT NOT NULL,
    distance_m NUMERIC(10,2) NOT NULL,
    buildings_count INTEGER NOT NULL DEFAULT 0,
    hydrants_count INTEGER NOT NULL DEFAULT 0,
    street_lights_count INTEGER NOT NULL DEFAULT 0,
    catchbasins_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    requested_asset_types TEXT[] NOT NULL,

    CONSTRAINT chk_requested_asset_types
        CHECK (
            cardinality(requested_asset_types) >= 1
            AND requested_asset_types <@ ARRAY[
                'buildings',
                'hydrants',
                'street_lights',
                'catchbasins'
            ]::TEXT[]
        )
);
