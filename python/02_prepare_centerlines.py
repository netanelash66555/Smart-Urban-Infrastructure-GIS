import geopandas as gpd

input_path = r"data\raw\TRANS_Centerlines.shp\TRANS_Centerlines.shp"
output_path = r"data\processed\roads.gpkg"

roads = gpd.read_file(input_path)

# Remove records without geometry
roads = roads[roads.geometry.notna()].copy()

# Keep only fields relevant to the project
roads = roads[
    [
        "ID",
        "Street_ID",
        "Street",
        "Street_Nam",
        "Street_Typ",
        "MajorRoad",
        "Direction",
        "Restrictio",
        "geometry",
    ]
]

# Reproject from feet to meters
roads = roads.to_crs(epsg=26986)

print("Rows after cleaning:", len(roads))
print("CRS after reprojection:", roads.crs)
print("Invalid geometries:", (~roads.geometry.is_valid).sum())

# Save the processed layer
roads.to_file(output_path, layer="roads", driver="GPKG")

print("Processed roads saved successfully.")