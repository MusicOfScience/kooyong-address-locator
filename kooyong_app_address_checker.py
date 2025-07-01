# 🗺️ Kooyong Electorate Address Checker + Street Map Viewer
import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderUnavailable, GeocoderTimedOut
import time
import json
import os
import zipfile

# Setup
st.set_page_config(page_title="Kooyong Address Checker", layout="wide")
st.title("🗺️ Kooyong Streets with Suburb Lookup")

# 🔧 Select Map Style
style = st.selectbox("Choose a map style:", [
    "OpenStreetMap", "Stamen Toner", "Stamen Terrain", "CartoDB Positron", "CartoDB Dark_Matter"
])

# 🏘️ Input Address
address_input = st.text_input("Enter a street address in Victoria:")

# 📥 Load street-suburb lookup CSV
@st.cache_data(show_spinner=False)
def load_street_lookup():
    return pd.read_csv("kooyong_street_suburb_lookup.csv")

lookup_df = load_street_lookup()

# 🧭 Load Kooyong boundary shapefile
@st.cache_data(show_spinner=False)
def load_kooyong_boundary():
    zip_path = "Vic-october-2024-esri.zip"
    extract_dir = "extracted_shapefiles"
    if not os.path.exists(extract_dir):
        os.makedirs(extract_dir)
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_dir)
    shp_file = None
    for root, dirs, files in os.walk(extract_dir):
        for f in files:
            if f.endswith(".shp"):
                shp_file = os.path.join(root, f)
                break
    gdf = gpd.read_file(shp_file)
    return gdf[gdf["Elect_div"] == "Kooyong"]

kooyong_gdf = load_kooyong_boundary()
kooyong_geom = kooyong_gdf.geometry.unary_union

# 🌍 Pull OSM streets using polygon
@st.cache_data(show_spinner=False)
def get_osm_street_geometries(kooyong_polygon):
    import osmnx as ox
    ox.settings.log_console = True
    ox.settings.use_cache = True
    tags = {"highway": True}
    gdf = ox.features_from_polygon(kooyong_polygon, tags=tags)
    gdf = gdf[["geometry", "name"]].dropna(subset=["name"])
    gdf = gdf[gdf.geometry.geom_type.isin(["LineString", "MultiLineString"])]
    gdf["name_lower"] = gdf["name"].str.lower()
    return gdf

osm_streets = get_osm_street_geometries(kooyong_geom)

# 📦 Join OSM geometries to suburb names
street_geom_merged = pd.merge(
    osm_streets,
    lookup_df,
    how="left",
    left_on="name_lower",
    right_on="street_lower"
)

# 🗺️ Display map with street overlays
m = folium.Map(location=[-37.82, 145.05], zoom_start=13, tiles=style)

# Kooyong boundary
folium.GeoJson(
    kooyong_geom,
    name="Kooyong Boundary",
    style_function=lambda x: {
        "fillOpacity": 0,
        "color": "teal",
        "weight": 2,
    }
).add_to(m)

# Street tooltips
for _, row in street_geom_merged.iterrows():
    if pd.notna(row.get("geometry")):
        tooltip = f"{row.get('street_name', row.get('name'))} → {row.get('suburb', 'Unknown')}"
        folium.GeoJson(
            row["geometry"],
            tooltip=tooltip,
            style_function=lambda x: {
                "color": "orange",
                "weight": 2,
                "opacity": 0.7
            }
        ).add_to(m)

st_folium(m, width=1000, height=600)

# 🧭 Geocode address (no bounding box bias)
if address_input.strip():
    geolocator = Nominatim(user_agent="kooyong_locator_app")
    time.sleep(1)
    try:
        location = geolocator.geocode(
            f"{address_input}, Victoria, Australia",
            country_codes="au",
            addressdetails=True
        )
        if location:
            st.success(f"📍 Found: {location.address}")
            st.write(f"📌 Latitude: {location.latitude}, Longitude: {location.longitude}")
            point = Point(location.longitude, location.latitude)
            if kooyong_geom.contains(point):
                st.success("✅ This address is in Kooyong.")
            else:
                st.warning("🚫 This address is outside Kooyong.")
        else:
            st.warning("⚠️ Could not geocode address.")
    except (GeocoderUnavailable, GeocoderTimedOut):
        st.error("⏳ Geocoding service temporarily unavailable.")
