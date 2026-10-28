from pathlib import Path
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


# ==================================================
# Configuration
# ==================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")

ALLOWED_ASSET_TYPES = [
    "buildings",
    "hydrants",
    "street_lights",
    "catchbasins"
]


# ==================================================
# Database connection
# ==================================================

def get_database_engine():

    connection_url = URL.create(
        drivername="postgresql+psycopg",
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT")),
        database=os.getenv("DB_NAME"),
    )

    return create_engine(
        connection_url,
        pool_pre_ping=True
    )


# ==================================================
# Validation
# ==================================================

def validate_distance(distance_m):

    if not isinstance(distance_m, (int, float)):
        raise ValueError(
            "Distance must be numeric."
        )

    if distance_m <= 0 or distance_m > 5000:
        raise ValueError(
            "Distance must be between 1 and 5000 meters."
        )


def validate_asset_types(asset_types):

    if not isinstance(asset_types, list):
        raise ValueError(
            "Asset types must be provided as a list."
        )

    if not asset_types:
        raise ValueError(
            "At least one asset type must be selected."
        )

    invalid_assets = [
        asset
        for asset in asset_types
        if asset not in ALLOWED_ASSET_TYPES
    ]

    if invalid_assets:
        raise ValueError(
            f"Unsupported asset types: {invalid_assets}"
        )


# ==================================================
# Find nearest road from map click
# ==================================================

def find_nearest_road(latitude, longitude):

    sql = text(
        """
        WITH click_point AS (
            SELECT ST_Transform(
                ST_SetSRID(
                    ST_MakePoint(
                        :longitude,
                        :latitude
                    ),
                    4326
                ),
                26986
            ) AS geom
        )

        SELECT
            r.road_id,
            r.street_name,
            ST_AsText(r.geom) AS geometry_wkt,

            ROUND(
                ST_Distance(
                    r.geom,
                    cp.geom
                )::numeric,
                2
            ) AS distance_m

        FROM gis.roads AS r
        CROSS JOIN click_point AS cp

        ORDER BY
            r.geom <-> cp.geom

        LIMIT 1;
        """
    )

    engine = get_database_engine()

    with engine.connect() as connection:

        result = connection.execute(
            sql,
            {
                "latitude": latitude,
                "longitude": longitude
            }
        )

        return result.mappings().first()


# ==================================================
# Spatial impact summary
# ==================================================

def run_spatial_impact_analysis(
    geometry_wkt,
    distance_m
):

    validate_distance(distance_m)

    sql = text(
        """
        WITH analysis_geometry AS (
            SELECT ST_SetSRID(
                ST_GeomFromText(:geometry_wkt),
                26986
            ) AS geom
        )

        SELECT

            (
                SELECT COUNT(*)
                FROM gis.buildings AS b
                CROSS JOIN analysis_geometry AS ag
                WHERE ST_DWithin(
                    b.geom,
                    ag.geom,
                    :distance_m
                )
            ) AS buildings,

            (
                SELECT COUNT(*)
                FROM gis.hydrants AS h
                CROSS JOIN analysis_geometry AS ag
                WHERE ST_DWithin(
                    h.geom,
                    ag.geom,
                    :distance_m
                )
            ) AS hydrants,

            (
                SELECT COUNT(*)
                FROM gis.street_lights AS sl
                CROSS JOIN analysis_geometry AS ag
                WHERE ST_DWithin(
                    sl.geom,
                    ag.geom,
                    :distance_m
                )
            ) AS street_lights,

            (
                SELECT COUNT(*)
                FROM gis.catchbasins AS c
                CROSS JOIN analysis_geometry AS ag
                WHERE ST_DWithin(
                    c.geom,
                    ag.geom,
                    :distance_m
                )
            ) AS catchbasins;
        """
    )

    engine = get_database_engine()

    with engine.connect() as connection:

        result = connection.execute(
            sql,
            {
                "geometry_wkt": geometry_wkt,
                "distance_m": distance_m
            }
        )

        return result.mappings().first()


# ==================================================
# Detailed affected assets
# ==================================================

def get_affected_assets(
    geometry_wkt,
    distance_m,
    asset_types
):

    validate_distance(distance_m)
    validate_asset_types(asset_types)

    queries = {

        "buildings": """
            WITH analysis_geometry AS (
                SELECT ST_SetSRID(
                    ST_GeomFromText(:geometry_wkt),
                    26986
                ) AS geom
            )

            SELECT
                b.building_id,
                b.source_id,
                b.building_type,

                ROUND(
                    ST_Distance(
                        b.geom,
                        ag.geom
                    )::numeric,
                    2
                ) AS distance_m

            FROM gis.buildings AS b
            CROSS JOIN analysis_geometry AS ag

            WHERE ST_DWithin(
                b.geom,
                ag.geom,
                :distance_m
            )

            ORDER BY distance_m, b.building_id;
        """,

        "hydrants": """
            WITH analysis_geometry AS (
                SELECT ST_SetSRID(
                    ST_GeomFromText(:geometry_wkt),
                    26986
                ) AS geom
            )

            SELECT
                h.hydrant_id,
                h.source_id,

                ROUND(
                    ST_Distance(
                        h.geom,
                        ag.geom
                    )::numeric,
                    2
                ) AS distance_m

            FROM gis.hydrants AS h
            CROSS JOIN analysis_geometry AS ag

            WHERE ST_DWithin(
                h.geom,
                ag.geom,
                :distance_m
            )

            ORDER BY distance_m, h.hydrant_id;
        """,

        "street_lights": """
            WITH analysis_geometry AS (
                SELECT ST_SetSRID(
                    ST_GeomFromText(:geometry_wkt),
                    26986
                ) AS geom
            )

            SELECT
                sl.light_id,
                sl.source_id,
                sl.street_name,

                ROUND(
                    ST_Distance(
                        sl.geom,
                        ag.geom
                    )::numeric,
                    2
                ) AS distance_m

            FROM gis.street_lights AS sl
            CROSS JOIN analysis_geometry AS ag

            WHERE ST_DWithin(
                sl.geom,
                ag.geom,
                :distance_m
            )

            ORDER BY distance_m, sl.light_id;
        """,

        "catchbasins": """
            WITH analysis_geometry AS (
                SELECT ST_SetSRID(
                    ST_GeomFromText(:geometry_wkt),
                    26986
                ) AS geom
            )

            SELECT
                c.catchbasin_id,
                c.facility_id,
                c.address,

                ROUND(
                    ST_Distance(
                        c.geom,
                        ag.geom
                    )::numeric,
                    2
                ) AS distance_m

            FROM gis.catchbasins AS c
            CROSS JOIN analysis_geometry AS ag

            WHERE ST_DWithin(
                c.geom,
                ag.geom,
                :distance_m
            )

            ORDER BY distance_m, c.catchbasin_id;
        """
    }

    engine = get_database_engine()

    results = {}

    with engine.connect() as connection:

        for asset_type in asset_types:

            rows = connection.execute(
                text(queries[asset_type]),
                {
                    "geometry_wkt": geometry_wkt,
                    "distance_m": distance_m
                }
            ).mappings().all()

            results[asset_type] = [
                dict(row)
                for row in rows
            ]

    return results


# ==================================================
# Save completed analysis run
# ==================================================

def save_analysis_run(
    road_id,
    distance_m,
    analysis,
    requested_asset_types
):

    validate_distance(distance_m)
    validate_asset_types(
        requested_asset_types
    )

    sql = text(
        """
        INSERT INTO gis.analysis_runs (
            road_id,
            distance_m,
            buildings_count,
            hydrants_count,
            street_lights_count,
            catchbasins_count,
            requested_asset_types
        )

        VALUES (
            :road_id,
            :distance_m,
            :buildings_count,
            :hydrants_count,
            :street_lights_count,
            :catchbasins_count,
            string_to_array(
                :requested_asset_types_csv,
                ','
            )
        )

        RETURNING analysis_id;
        """
    )

    engine = get_database_engine()

    with engine.begin() as connection:

        result = connection.execute(
            sql,
            {
                "road_id": road_id,
                "distance_m": distance_m,
                "buildings_count": analysis["buildings"],
                "hydrants_count": analysis["hydrants"],
                "street_lights_count": analysis["street_lights"],
                "catchbasins_count": analysis["catchbasins"],
                "requested_asset_types_csv": ",".join(
                    requested_asset_types
                )
            }
        )

        return result.scalar_one()


# ==================================================
# Analysis history
# ==================================================

def get_analysis_history(limit=100):

    sql = text(
        """
        SELECT
            ar.analysis_id,
            ar.road_id,
            r.street_name,
            ar.distance_m,
            ar.requested_asset_types,

            (
                CASE
                    WHEN 'buildings'
                        = ANY(ar.requested_asset_types)
                    THEN ar.buildings_count
                    ELSE 0
                END

                +

                CASE
                    WHEN 'hydrants'
                        = ANY(ar.requested_asset_types)
                    THEN ar.hydrants_count
                    ELSE 0
                END

                +

                CASE
                    WHEN 'street_lights'
                        = ANY(ar.requested_asset_types)
                    THEN ar.street_lights_count
                    ELSE 0
                END

                +

                CASE
                    WHEN 'catchbasins'
                        = ANY(ar.requested_asset_types)
                    THEN ar.catchbasins_count
                    ELSE 0
                END
            ) AS requested_total,

            ar.buildings_count,
            ar.hydrants_count,
            ar.street_lights_count,
            ar.catchbasins_count,

            ar.created_at

        FROM gis.analysis_runs AS ar

        JOIN gis.roads AS r
            ON ar.road_id = r.road_id

        ORDER BY ar.created_at DESC

        LIMIT :limit;
        """
    )

    engine = get_database_engine()

    with engine.connect() as connection:

        result = connection.execute(
            sql,
            {
                "limit": limit
            }
        )

        return [
            dict(row)
            for row in result.mappings().all()
        ]


# ==================================================
# Get one historical analysis run
# ==================================================

def get_analysis_run_context(
    analysis_id
):

    sql = text(
        """
        SELECT
            ar.analysis_id,
            ar.road_id,
            r.street_name,
            ar.distance_m,
            ar.requested_asset_types,

            ar.buildings_count,
            ar.hydrants_count,
            ar.street_lights_count,
            ar.catchbasins_count,

            ar.created_at,

            ST_AsText(
                r.geom
            ) AS geometry_wkt

        FROM gis.analysis_runs AS ar

        JOIN gis.roads AS r
            ON ar.road_id = r.road_id

        WHERE ar.analysis_id = :analysis_id;
        """
    )

    engine = get_database_engine()

    with engine.connect() as connection:

        result = connection.execute(
            sql,
            {
                "analysis_id": analysis_id
            }
        )

        row = result.mappings().first()

    if row is None:
        raise ValueError(
            f"Analysis run {analysis_id} was not found."
        )

    run_context = dict(row)

    run_context[
        "requested_asset_types"
    ] = list(
        run_context[
            "requested_asset_types"
        ]
    )

    return run_context