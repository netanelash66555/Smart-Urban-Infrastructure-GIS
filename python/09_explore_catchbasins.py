import geopandas as gpd

file_path = r"data\raw\INFRA_Catchbasin.shp\INFRA_Catchbasin.shp"

catchbasins = gpd.read_file(file_path)

print("Rows:", len(catchbasins))

print("\nColumns:")
print(catchbasins.columns.tolist())

print("\nCRS:")
print(catchbasins.crs)

print("\nGeometry types:")
print(catchbasins.geom_type.value_counts())

print("\nMissing values:")
print(catchbasins.isna().sum())

print("\nInvalid geometries:")
print((~catchbasins.geometry.is_valid).sum())

print("\nMissing FACILITYID:")
print(catchbasins["FACILITYID"].isna().sum())

print("\nDuplicate non-null FACILITYID:")
print(
    catchbasins["FACILITYID"]
    .dropna()
    .duplicated()
    .sum()
)