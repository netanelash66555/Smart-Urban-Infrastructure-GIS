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
street_lights_path = (
    project_root
    / "data"
    / "processed"
    / "street_lights.gpkg"
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
# 4. Read processed street lights
# -----------------------------

street_lights = gpd.read_file(
    street_lights_path,
    layer="street_lights"
)

print("Rows read from GeoPackage:", len(street_lights))
print("CRS:", street_lights.crs)


# -----------------------------
# 5. Rename columns
# -----------------------------

street_lights = street_lights.rename(
    columns={
        "PoleID": "source_id",
        "Street_ID": "street_id",
        "StreetName": "street_name",
        "Owner": "owner",
        "FixtureTyp": "fixture_type",
        "NumLamps": "num_lamps",
        "LEDchk": "led_status",
        "Neighborho": "neighborhood",
    }
)

street_lights = street_lights.rename_geometry("geom")


# -----------------------------
# 6. Load into PostGIS
# -----------------------------

street_lights.to_postgis(
    name="street_lights",
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
            ALTER TABLE gis.street_lights
            ADD COLUMN light_id BIGSERIAL PRIMARY KEY;
        """)
    )


# -----------------------------
# 8. Verify load
# -----------------------------

with engine.connect() as connection:
    row_count = connection.execute(
        text("SELECT COUNT(*) FROM gis.street_lights;")
    ).scalar()


print("Street lights loaded successfully.")
print("Rows in PostGIS:", row_count)