import geopandas as gpd

file_path = r"data\raw\INFRA_StreetLights.shp\INFRA_StreetLights.shp"

lights = gpd.read_file(file_path)

print("Rows:", len(lights))

print("\nColumns:")
print(lights.columns.tolist())

print("\nCRS:")
print(lights.crs)

print("\nGeometry types:")
print(lights.geom_type.value_counts())

print("\nMissing values:")
print(lights.isna().sum())

print("\nInvalid geometries:")
print((~lights.geometry.is_valid).sum())

print("\nMissing PoleID:")
print(lights["PoleID"].isna().sum())

print("\nDuplicate non-null PoleID:")
print(lights["PoleID"].dropna().duplicated().sum())