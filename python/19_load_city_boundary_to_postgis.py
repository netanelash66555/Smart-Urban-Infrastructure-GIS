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
boundary_path = (
    project_root
    / "data"
    / "processed"
    / "city_boundary.gpkg"
)


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
# 4. Read processed city boundary
# -----------------------------

boundary = gpd.read_file(
    boundary_path,
    layer="city_boundary"
)

print("Rows read from GeoPackage:", len(boundary))
print("CRS:", boundary.crs)


# -----------------------------
# 5. Rename columns
# -----------------------------

boundary = boundary.rename(
    columns={
        "GlobalID": "source_id",
    }
)

boundary["city_name"] = "Cambridge"

boundary = boundary.rename_geometry("geom")


# -----------------------------
# 6. Load into PostGIS
# -----------------------------

boundary.to_postgis(
    name="city_boundary",
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
            ALTER TABLE gis.city_boundary
            ADD COLUMN boundary_id BIGSERIAL PRIMARY KEY;
        """)
    )


# -----------------------------
# 8. Verify load
# -----------------------------

with engine.connect() as connection:
    row_count = connection.execute(
        text("SELECT COUNT(*) FROM gis.city_boundary;")
    ).scalar()


print("City boundary loaded successfully.")
print("Rows in PostGIS:", row_count)