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
# 2. Create PostgreSQL connection
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
# 3. Reusable impact analysis function
# --------------------------------

def run_impact_analysis(road_id, distance_m):

    # -----------------------------
    # Validate input
    # -----------------------------

    if not isinstance(road_id, int):
        raise ValueError("road_id must be an integer.")

    if road_id <= 0:
        raise ValueError("road_id must be greater than 0.")

    if not isinstance(distance_m, (int, float)):
        raise ValueError("distance_m must be a number.")

    if distance_m <= 0:
        raise ValueError("distance_m must be greater than 0.")

    if distance_m > 5000:
        raise ValueError("distance_m is too large.")


    # -----------------------------
    # Parameterized Spatial SQL
    # -----------------------------

    query = text("""
        WITH selected_road AS (
            SELECT
                road_id,
                street_name,
                geom
            FROM gis.roads
            WHERE road_id = :road_id
        ),

        road_buffer AS (
            SELECT
                road_id,
                street_name,
                geom AS road_geom,
                ST_Buffer(geom, :distance_m) AS buffer_geom
            FROM selected_road
        )

        SELECT
            rb.road_id,
            rb.street_name,
            :distance_m AS buffer_distance_m,

            (
                SELECT COUNT(*)
                FROM gis.buildings AS b
                WHERE ST_Intersects(
                    b.geom,
                    rb.buffer_geom
                )
            ) AS affected_buildings,

            (
                SELECT COUNT(*)
                FROM gis.hydrants AS h
                WHERE ST_DWithin(
                    h.geom,
                    rb.road_geom,
                    :distance_m
                )
            ) AS affected_hydrants,

            (
                SELECT COUNT(*)
                FROM gis.street_lights AS sl
                WHERE ST_DWithin(
                    sl.geom,
                    rb.road_geom,
                    :distance_m
                )
            ) AS affected_street_lights,

            (
                SELECT COUNT(*)
                FROM gis.catchbasins AS c
                WHERE ST_DWithin(
                    c.geom,
                    rb.road_geom,
                    :distance_m
                )
            ) AS affected_catchbasins

        FROM road_buffer AS rb;
    """)


    # -----------------------------
    # Execute query
    # -----------------------------

    with engine.connect() as connection:

        result = connection.execute(
            query,
            {
                "road_id": road_id,
                "distance_m": distance_m,
            }
        ).mappings().first()


    if result is None:
        raise ValueError("Road not found.")


    return dict(result)


# --------------------------------
# 4. Test the function
# --------------------------------

result = run_impact_analysis(
    road_id=1,
    distance_m=300
)

print("\nImpact Analysis")
print("-----------------------------")
print("Road ID:", result["road_id"])
print("Street:", result["street_name"])
print("Buffer distance:", result["buffer_distance_m"], "meters")
print("Buildings:", result["affected_buildings"])
print("Hydrants:", result["affected_hydrants"])
print("Street lights:", result["affected_street_lights"])
print("Catchbasins:", result["affected_catchbasins"])