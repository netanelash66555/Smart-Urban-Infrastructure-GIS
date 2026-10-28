import geopandas as gpd

input_path = r"data\raw\INFRA_StreetLights.shp\INFRA_StreetLights.shp"
output_path = r"data\processed\street_lights.gpkg"

lights = gpd.read_file(input_path)

# Check whether the same records are missing both geometry and PoleID
both_missing = (
    lights["geometry"].isna()
    & lights["PoleID"].isna()
).sum()

print("Rows before cleaning:", len(lights))
print("Rows missing both geometry and PoleID:", both_missing)

# Remove records without spatial location
lights = lights[lights.geometry.notna()].copy()

# Keep fields relevant to our use case
lights = lights[
    [
        "PoleID",
        "Street_ID",
        "StreetName",
        "Owner",
        "FixtureTyp",
        "NumLamps",
        "LEDchk",
        "Neighborho",
        "geometry",
    ]
]

# Reproject from feet to meters
lights = lights.to_crs(epsg=26986)

# Final checks
print("Rows after cleaning:", len(lights))
print("Missing PoleID after cleaning:", lights["PoleID"].isna().sum())
print("Duplicate PoleID:", lights["PoleID"].dropna().duplicated().sum())
print("CRS:", lights.crs)
print("Invalid geometries:", (~lights.geometry.is_valid).sum())

# Save processed layer
lights.to_file(
    output_path,
    layer="street_lights",
    driver="GPKG"
)

print("Processed street lights saved successfully.")