import geopandas as gpd

file_path = r"data\raw\BOUNDARY_CityBoundary.shp\BOUNDARY_CityBoundary.shp"

boundary = gpd.read_file(file_path)

print("Rows:", len(boundary))

print("\nColumns:")
print(boundary.columns.tolist())

print("\nCRS:")
print(boundary.crs)

print("\nGeometry types:")
print(boundary.geom_type.value_counts())

print("\nMissing values:")
print(boundary.isna().sum())

print("\nInvalid geometries:")
print((~boundary.geometry.is_valid).sum())

print("\nMissing GlobalID:")
print(boundary["GlobalID"].isna().sum())