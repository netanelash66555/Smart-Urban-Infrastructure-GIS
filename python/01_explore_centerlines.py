import geopandas as gpd

file_path = r"data\raw\TRANS_Centerlines.shp\TRANS_Centerlines.shp"

roads = gpd.read_file(file_path)

print("Rows:", len(roads))

print("\nColumns:")
print(roads.columns.tolist())

print("\nCRS:")
print(roads.crs)

print("\nGeometry types:")
print(roads.geom_type.value_counts())

print("\nMissing values:")
print(roads.isna().sum())

print("\nInvalid geometries:")
print((~roads.geometry.is_valid).sum())