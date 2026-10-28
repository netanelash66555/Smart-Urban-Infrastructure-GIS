import os
from pathlib import Path

import geopandas as gpd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


# --------------------------------
# 1. Project settings
# --------------------------------

project_root = Path(__file__).resolve().parent.parent
env_path = project_root / ".env"

output_path = (
    project_root
    / "data"
    / "processed"
    / "impact_analysis.gpkg"
)

load_dotenv(env_path)


# --------------------------------
# 2. Database connection
# --------------------------------

connection_url = URL.create(
    drivername="postgresql+psycopg",
    username=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT")),
    database=os.getenv("DB_NAME"),
)

engine = create_engine(connection_url)


# --------------------------------
# 3. Analysis parameters
# --------------------------------

road_id = 1
distance_m = 300


# --------------------------------
# 4. Selected road
# --------------------------------

road_query = text("""
    SELECT
        road_id,
        street_name,
        geom
    FROM gis.roads
    WHERE road_id = :road_id;
""")

selected_road = gpd.read_postgis(
    road_query,
    engine,
    geom_col="geom",
    params={"road_id": road_id}
)


# --------------------------------
# 5. Impact zone
# --------------------------------

buffer_query = text("""
    SELECT
        road_id,
        street_name,
        ST_Buffer(
            geom,
            :distance_m
        ) AS geom
    FROM gis.roads
    WHERE road_id = :road_id;
""")

impact_zone = gpd.read_postgis(
    buffer_query,
    engine,
    geom_col="geom",
    params={
        "road_id": road_id,
        "distance_m": distance_m,
    }
)


# --------------------------------
# 6. Affected assets
# --------------------------------

asset_queries = {

    "affected_buildings": """
        SELECT b.*
        FROM gis.buildings AS b
        JOIN gis.roads AS r
          ON ST_DWithin(
                b.geom,
                r.geom,
                :distance_m
             )
        WHERE r.road_id = :road_id;
    """,

    "affected_hydrants": """
        SELECT h.*
        FROM gis.hydrants AS h
        JOIN gis.roads AS r
          ON ST_DWithin(
                h.geom,
                r.geom,
                :distance_m
             )
        WHERE r.road_id = :road_id;
    """,

    "affected_street_lights": """
        SELECT sl.*
        FROM gis.street_lights AS sl
        JOIN gis.roads AS r
          ON ST_DWithin(
                sl.geom,
                r.geom,
                :distance_m
             )
        WHERE r.road_id = :road_id;
    """,

    "affected_catchbasins": """
        SELECT c.*
        FROM gis.catchbasins AS c
        JOIN gis.roads AS r
          ON ST_DWithin(
                c.geom,
                r.geom,
                :distance_m
             )
        WHERE r.road_id = :road_id;
    """
}


results = {}

for layer_name, sql in asset_queries.items():

    results[layer_name] = gpd.read_postgis(
        text(sql),
        engine,
        geom_col="geom",
        params={
            "road_id": road_id,
            "distance_m": distance_m,
        }
    )


# --------------------------------
# 7. Export results to GeoPackage
# --------------------------------

if output_path.exists():
    output_path.unlink()


selected_road.to_file(
    output_path,
    layer="selected_road",
    driver="GPKG"
)

impact_zone.to_file(
    output_path,
    layer="impact_zone",
    driver="GPKG"
)


for layer_name, gdf in results.items():

    gdf.to_file(
        output_path,
        layer=layer_name,
        driver="GPKG"
    )


# --------------------------------
# 8. Summary
# --------------------------------

print("\nImpact analysis exported successfully.")
print("--------------------------------------")
print("Street:", selected_road.iloc[0]["street_name"])
print("Road ID:", road_id)
print("Distance:", distance_m, "meters")
print("Buildings:", len(results["affected_buildings"]))
print("Hydrants:", len(results["affected_hydrants"]))
print("Street lights:", len(results["affected_street_lights"]))
print("Catchbasins:", len(results["affected_catchbasins"]))
print("\nOutput:")
print(output_path)