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
catchbasins_path = (
    project_root
    / "data"
    / "processed"
    / "catchbasins.gpkg"
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
# 4. Read processed catchbasins
# -----------------------------

catchbasins = gpd.read_file(
    catchbasins_path,
    layer="catchbasins"
)

print("Rows read from GeoPackage:", len(catchbasins))
print("CRS:", catchbasins.crs)


# -----------------------------
# 5. Rename columns
# -----------------------------

catchbasins = catchbasins.rename(
    columns={
        "FACILITYID": "facility_id",
        "GlobalID": "global_id",
        "WATERTYPE": "water_type",
        "LIFECYCLES": "lifecycle_status",
        "OWNER": "owner",
        "INSTALLDAT": "install_date",
        "ADDRESS": "address",
        "DEPTH": "depth",
        "Watershed": "watershed",
    }
)

catchbasins = catchbasins.rename_geometry("geom")


# -----------------------------
# 6. Load into PostGIS
# -----------------------------

catchbasins.to_postgis(
    name="catchbasins",
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
            ALTER TABLE gis.catchbasins
            ADD COLUMN catchbasin_id BIGSERIAL PRIMARY KEY;
        """)
    )


# -----------------------------
# 8. Verify load
# -----------------------------

with engine.connect() as connection:
    row_count = connection.execute(
        text("SELECT COUNT(*) FROM gis.catchbasins;")
    ).scalar()


print("Catchbasins loaded successfully.")
print("Rows in PostGIS:", row_count)