import os
from pathlib import Path

import geopandas as gpd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


# -----------------------------
# 1. Project paths
# -----------------------------

project_root = Path(__file__).resolve().parent.parent

env_path = project_root / ".env"
buildings_path = project_root / "data" / "processed" / "buildings.gpkg"


# -----------------------------
# 2. Load database settings
# -----------------------------

load_dotenv(env_path)

db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")


# -----------------------------
# 3. Create PostgreSQL connection
# -----------------------------

connection_url = URL.create(
    drivername="postgresql+psycopg",
    username=db_user,
    password=db_password,
    host=db_host,
    port=int(db_port),
    database=db_name,
)

engine = create_engine(connection_url)


# -----------------------------
# 4. Read processed buildings
# -----------------------------

buildings = gpd.read_file(
    buildings_path,
    layer="buildings"
)

print("Rows read from GeoPackage:", len(buildings))
print("CRS:", buildings.crs)


# -----------------------------
# 5. Rename columns
# -----------------------------

buildings = buildings.rename(
    columns={
        "BldgID": "source_id",
        "TYPE": "building_type",
    }
)

buildings = buildings.rename_geometry("geom")


# -----------------------------
# 6. Load into PostGIS
# -----------------------------

buildings.to_postgis(
    name="buildings",
    con=engine,
    schema="gis",
    if_exists="replace",
    index=False,
)


# -----------------------------
# 7. Add internal Primary Key
# -----------------------------

with engine.begin() as connection:
    connection.execute(
        text("""
            ALTER TABLE gis.buildings
            ADD COLUMN building_id BIGSERIAL PRIMARY KEY;
        """)
    )


# -----------------------------
# 8. Verify load
# -----------------------------

with engine.connect() as connection:
    row_count = connection.execute(
        text("SELECT COUNT(*) FROM gis.buildings;")
    ).scalar()


print("Buildings loaded successfully.")
print("Rows in PostGIS:", row_count)