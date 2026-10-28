import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


# --------------------------------
# 1. Project and database settings
# --------------------------------

project_root = Path(__file__).resolve().parent.parent
env_path = project_root / ".env"

load_dotenv(env_path)

db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")


# --------------------------------
# 2. PostgreSQL connection
# --------------------------------

connection_url = URL.create(
    drivername="postgresql+psycopg",
    username=db_user,
    password=db_password,
    host=db_host,
    port=int(db_port),
    database=db_name,
)

engine = create_engine(connection_url)


# --------------------------------
# 3. Get road geometry
# --------------------------------

def get_road_geometry(road_id):

    if not isinstance(road_id, int):
        raise ValueError("road_id must be an integer.")

    if road_id <= 0:
        raise ValueError("road_id must be greater than 0.")

    query = text("""
        SELECT
            road_id,
            street_name,
            ST_AsText(geom) AS geometry_wkt
        FROM gis.roads
        WHERE road_id = :road_id;
    """)

    with engine.connect() as connection:

        result = connection.execute(
            query,
            {
                "road_id": road_id
            }
        ).mappings().first()

    if result is None:
        raise ValueError("Road not found.")

    return dict(result)


# --------------------------------
# 4. Generic spatial impact engine
# --------------------------------

def run_spatial_impact_analysis(
    geometry_wkt,
    distance_m
):

    if not isinstance(distance_m, (int, float)):
        raise ValueError("distance_m must be numeric.")

    if distance_m <= 0:
        raise ValueError("distance_m must be greater than 0.")

    if distance_m > 5000:
        raise ValueError("distance_m is too large.")

    query = text("""
        WITH analysis_geometry AS (
            SELECT
                ST_GeomFromText(
                    :geometry_wkt,
                    26986
                ) AS geom
        )

        SELECT
            :distance_m AS buffer_distance_m,

            (
                SELECT COUNT(*)
                FROM gis.buildings AS b,
                     analysis_geometry AS ag
                WHERE ST_DWithin(
                    b.geom,
                    ag.geom,
                    :distance_m
                )
            ) AS affected_buildings,

            (
                SELECT COUNT(*)
                FROM gis.hydrants AS h,
                     analysis_geometry AS ag
                WHERE ST_DWithin(
                    h.geom,
                    ag.geom,
                    :distance_m
                )
            ) AS affected_hydrants,

            (
                SELECT COUNT(*)
                FROM gis.street_lights AS sl,
                     analysis_geometry AS ag
                WHERE ST_DWithin(
                    sl.geom,
                    ag.geom,
                    :distance_m
                )
            ) AS affected_street_lights,

            (
                SELECT COUNT(*)
                FROM gis.catchbasins AS c,
                     analysis_geometry AS ag
                WHERE ST_DWithin(
                    c.geom,
                    ag.geom,
                    :distance_m
                )
            ) AS affected_catchbasins;
    """)

    with engine.connect() as connection:

        result = connection.execute(
            query,
            {
                "geometry_wkt": geometry_wkt,
                "distance_m": distance_m,
            }
        ).mappings().first()

    return dict(result)


# --------------------------------
# 5. Test the engine
# --------------------------------

if __name__ == "__main__":

    road = get_road_geometry(1)

    result = run_spatial_impact_analysis(
        geometry_wkt=road["geometry_wkt"],
        distance_m=300
    )

    print("\nSpatial Impact Analysis")
    print("-----------------------------")
    print("Road ID:", road["road_id"])
    print("Street:", road["street_name"])
    print("Buffer distance:", result["buffer_distance_m"], "meters")
    print("Buildings:", result["affected_buildings"])
    print("Hydrants:", result["affected_hydrants"])
    print("Street lights:", result["affected_street_lights"])
    print("Catchbasins:", result["affected_catchbasins"])