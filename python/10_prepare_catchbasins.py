import geopandas as gpd

input_path = r"data\raw\INFRA_Catchbasin.shp\INFRA_Catchbasin.shp"
output_path = r"data\processed\catchbasins.gpkg"

catchbasins = gpd.read_file(input_path)

print("Rows before cleaning:", len(catchbasins))

# Keep only records that have a spatial location
catchbasins = catchbasins[
    catchbasins.geometry.notna()
].copy()

# Keep fields relevant to our project
catchbasins = catchbasins[
    [
        "FACILITYID",
        "GlobalID",
        "WATERTYPE",
        "LIFECYCLES",
        "OWNER",
        "INSTALLDAT",
        "ADDRESS",
        "DEPTH",
        "Watershed",
        "geometry",
    ]
]

# Reproject from feet to meters
catchbasins = catchbasins.to_crs(epsg=26986)

# Data-quality checks
duplicate_facility_ids = (
    catchbasins["FACILITYID"]
    .dropna()
    .duplicated()
    .sum()
)

duplicate_global_ids = (
    catchbasins["GlobalID"]
    .dropna()
    .duplicated()
    .sum()
)

print("Rows after cleaning:", len(catchbasins))
print("Duplicate FACILITYID:", duplicate_facility_ids)
print("Duplicate GlobalID:", duplicate_global_ids)
print("CRS:", catchbasins.crs)
print("Invalid geometries:", (~catchbasins.geometry.is_valid).sum())

# Save processed layer
catchbasins.to_file(
    output_path,
    layer="catchbasins",
    driver="GPKG"
)

print("Processed catchbasins saved successfully.")