import geopandas as gpd

input_path = r"data\raw\BASEMAP_Buildings.shp\BASEMAP_Buildings.shp"
output_path = r"data\processed\buildings.gpkg"

buildings = gpd.read_file(input_path)

# Remove records without geometry
buildings = buildings[buildings.geometry.notna()].copy()

# Keep only fields relevant to our project
buildings = buildings[
    [
        "BldgID",
        "TYPE",
        "geometry",
    ]
]

# Reproject to meter-based CRS
buildings = buildings.to_crs(epsg=26986)

print("Rows after cleaning:", len(buildings))
print("CRS after reprojection:", buildings.crs)
print("Invalid geometries:", (~buildings.geometry.is_valid).sum())

print("\nBuilding types after cleaning:")
print(buildings["TYPE"].value_counts(dropna=False))

# Save processed layer
buildings.to_file(
    output_path,
    layer="buildings",
    driver="GPKG"
)

print("\nProcessed buildings saved successfully.")