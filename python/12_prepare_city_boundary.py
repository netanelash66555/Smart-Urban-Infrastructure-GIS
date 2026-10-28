import geopandas as gpd

input_path = r"data\raw\BOUNDARY_CityBoundary.shp\BOUNDARY_CityBoundary.shp"
output_path = r"data\processed\city_boundary.gpkg"

boundary = gpd.read_file(input_path)

print("Rows before cleaning:", len(boundary))

# Keep only records with geometry
boundary = boundary[boundary.geometry.notna()].copy()

# Keep only fields relevant to our project
boundary = boundary[
    [
        "GlobalID",
        "geometry",
    ]
]

# Reproject from feet to meters
boundary = boundary.to_crs(epsg=26986)

print("Rows after cleaning:", len(boundary))
print("CRS:", boundary.crs)
print("Invalid geometries:", (~boundary.geometry.is_valid).sum())

# Save processed layer
boundary.to_file(
    output_path,
    layer="city_boundary",
    driver="GPKG"
)

print("Processed city boundary saved successfully.")