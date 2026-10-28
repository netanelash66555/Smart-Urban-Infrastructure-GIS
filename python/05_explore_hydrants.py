import geopandas as gpd

file_path = r"data\raw\INFRA_Hydrants.shp\INFRA_Hydrants.shp"

hydrants = gpd.read_file(file_path)

print("Rows:", len(hydrants))

print("\nColumns:")
print(hydrants.columns.tolist())

print("\nCRS:")
print(hydrants.crs)

print("\nGeometry types:")
print(hydrants.geom_type.value_counts())

print("\nMissing values:")
print(hydrants.isna().sum())

print("\nInvalid geometries:")
print((~hydrants.geometry.is_valid).sum())

print("\nDuplicate HYDRANT_ID values:")
print(hydrants["HYDRANT_ID"].duplicated().sum())