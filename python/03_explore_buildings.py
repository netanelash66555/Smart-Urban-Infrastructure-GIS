import geopandas as gpd

file_path = r"data\raw\BASEMAP_Buildings.shp\BASEMAP_Buildings.shp"

buildings = gpd.read_file(file_path)

print("Rows:", len(buildings))

print("\nColumns:")
print(buildings.columns.tolist())

print("\nCRS:")
print(buildings.crs)

print("\nGeometry types:")
print(buildings.geom_type.value_counts())

print("\nMissing values:")
print(buildings.isna().sum())

print("\nInvalid geometries:")
print((~buildings.geometry.is_valid).sum())

print("\nBuilding types:")
print(buildings["TYPE"].value_counts(dropna=False))