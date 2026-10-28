import geopandas as gpd

input_path = r"data\raw\INFRA_Hydrants.shp\INFRA_Hydrants.shp"
output_path = r"data\processed\hydrants.gpkg"

hydrants = gpd.read_file(input_path)

# Keep only records with valid spatial location
hydrants = hydrants[hydrants.geometry.notna()].copy()

# Keep only fields relevant to our project
hydrants = hydrants[
    [
        "HYDRANT_ID",
        "LIFECYCLES",
        "INSTALLDAT",
        "ENABLED",
        "ContractAu",
        "geometry",
    ]
]

# Reproject from feet-based CRS to meter-based CRS
hydrants = hydrants.to_crs(epsg=26986)

# Data quality checks
missing_ids = hydrants["HYDRANT_ID"].isna().sum()

duplicate_ids = (
    hydrants["HYDRANT_ID"]
    .dropna()
    .duplicated()
    .sum()
)

print("Rows:", len(hydrants))
print("Missing HYDRANT_ID:", missing_ids)
print("Duplicate non-null HYDRANT_ID:", duplicate_ids)
print("CRS:", hydrants.crs)
print("Invalid geometries:", (~hydrants.geometry.is_valid).sum())

# Save processed layer
hydrants.to_file(
    output_path,
    layer="hydrants",
    driver="GPKG"
)

print("Processed hydrants saved successfully.")