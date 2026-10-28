import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


# Find the .env file in the main project folder
project_root = Path(__file__).resolve().parent.parent
env_path = project_root / ".env"

# Load database settings from .env
load_dotenv(env_path)

db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")


# Build the PostgreSQL connection
connection_url = URL.create(
    drivername="postgresql+psycopg",
    username=db_user,
    password=db_password,
    host=db_host,
    port=int(db_port),
    database=db_name,
)

engine = create_engine(connection_url)


# Test the connection
with engine.connect() as connection:
    database_name = connection.execute(
        text("SELECT current_database();")
    ).scalar()

    postgis_version = connection.execute(
        text("SELECT PostGIS_Version();")
    ).scalar()


print("Connected successfully.")
print("Database:", database_name)
print("PostGIS:", postgis_version)