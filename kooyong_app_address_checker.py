# 📍 Kooyong Streets Visualiser with Real OSM Geometry
import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from shapely.geometry import Point, LineString, Polygon
from streamlit_folium import st_folium
import osmnx as ox
import zipfile
import os

st.set_page_config(page_title="Kooyong Streets Map", layout="wide")
st.title("🗺️ Kooyong Streets with Suburb Lookup")

# 📦 Load AEC Kooyong boundary from shapefile ZIP
@st.cache_data(show_spinner=False)
def load_kooyong_boundary():
    zip_path = "Vic-october-2024-esri.zip"
    extract_dir = "aec_boundary"
    if not os.path.exists(extract_dir):
        os.makedirs(extract_dir)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
    
    shp_path = None
    for root, dirs, files in os.walk(extract_dir):
        for f in files:
            if f.endswith(".shp"):
                shp_path = os.path.join(root, f)
                break

    gdf = gpd.read_file(shp_path)
    return gdf[gdf["Elect_div"] == "Kooyong"].to_crs(epsg=4326)

kooyong_gdf = load_kooyong_boundary()

# 🧠 Load Kooyong streets + suburbs CSV
@st.cache_data(show_spinner=False)
def load_street_csv():
    df = pd.read_csv("kooyong_street_suburb_lookup.csv")
    return df

df = load_street_csv()

# 🌐 Get real street geometries from OSM
@st.cache_data(show_spinner=True)
def get_osm_street_geometries(kooyong_poly):
    ox.settings.log_console = False
    ox.settings.use_cache = True
    tags = {"highway": True}
    osm_gdf = ox.geometries_from_polygon(kooyong_poly.geometry.iloc[0], tags)
    osm_gdf = osm_gdf[~osm_gdf["name"].isna()]
    return osm_gdf[["name", "geometry"]].reset_index(drop=True)

osm_streets = get_osm_street_geometries(kooyong_gdf)

# 🎯 Join street name lookups with OSM geometries
def merge_lookup_with_osm(df_lookup, gdf_osm):
    df_lookup["street_lower"] = df_lookup["street_name"].str.lower().str.strip()
    gdf_osm["street_lower"] = gdf_osm["name"].str.lower().str.strip()

    merged = pd.merge(gdf_osm, df_lookup, on="street_lower", how="inner")
    return gpd.GeoDataFrame(merged, geometry="geometry", crs="EPSG:4326")

streets_matched = merge_lookup_with_osm(df, osm_streets)

# 🗺️ Create map
m = folium.Map(location=[-37.82, 145.05], zoom_start=13, tiles="CartoDB Positron")

# Add Kooyong boundary
folium.GeoJson(
    kooyong_gdf.geometry.iloc[0],
    name="Kooyong Electorate",
    style_function=lambda x: {"color": "teal", "fillOpacity": 0.05}
).add_to(m)

# Add matched streets
for _, row in streets_matched.iterrows():
    folium.GeoJson(
        row["geometry"],
        tooltip=f"{row['street_name']} — {row['suburb']}",
        style_function=lambda x: {"color": "black", "weight": 2}
    ).add_to(m)

# Display map
st.markdown("### 🧭 Streets in Kooyong with known suburb matches")
st_data = st_folium(m, width=1000, height=600)
