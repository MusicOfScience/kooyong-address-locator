# 📍 Kooyong Address Checker & Map (Streamlit App)

import streamlit as st
import geopandas as gpd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
from shapely.geometry import Point
import zipfile
import os
import geopy
from geopy.geocoders import Nominatim

st.set_page_config(page_title="Kooyong Electorate Address Checker", layout="wide")

# --- CONFIG ---
ZIP_PATH = "Data/Vic-october-2024-esri.zip"
EXTRACT_DIR = "extracted_shapefiles"

# --- LOAD AND CACHE SHAPEFILE ---
@st.cache_data
def load_kooyong_boundary():
    if not os.path.exists(EXTRACT_DIR):
        os.makedirs(EXTRACT_DIR, exist_ok=True)
        with zipfile.ZipFile(ZIP_PATH, "r") as zip_ref:
            zip_ref.extractall(EXTRACT_DIR)

    # 🔍 Recursively search for .shp file
    shp_files = []
    for root, dirs, files in os.walk(EXTRACT_DIR):
        for file in files:
            if file.endswith(".shp"):
                shp_files.append(os.path.join(root, file))

    if not shp_files:
        st.error(f"❌ No .shp files found in {EXTRACT_DIR}. Contents: {os.listdir(EXTRACT_DIR)}")
        return None

    gdf = gpd.read_file(shp_files[0])
    return gdf[gdf["Elect_div"].str.contains("Kooyong", case=False)]

# --- GEOCODER ---
@st.cache_resource
def get_geolocator():
    return Nominatim(user_agent="kooyong_locator")

# --- STYLING ---
st.title("📍 Kooyong Electorate Address Checker")
address_input = st.text_input("Enter an address in Victoria:", placeholder="e.g. 123 High St, Kew")

map_style = st.selectbox("Choose a map style:", [
    "OpenStreetMap", "CartoDB positron", "Stamen Toner", "Stamen Terrain", "CartoDB dark_matter"
])

# --- RUN LOGIC ---
if address_input:
    geolocator = get_geolocator()
    location = geolocator.geocode(address_input)

    if not location:
        st.warning("⚠️ Could not geocode that address.")
    else:
        gdf = load_kooyong_boundary()
        if gdf is None:
            st.stop()

        address_point = Point(location.longitude, location.latitude)
        within = gdf.contains(address_point).any()

        if within:
            st.success("✅ Inside Kooyong")
        else:
            st.warning("🚫 Outside Kooyong")

        # --- RENDER MAP ---
        m = folium.Map(location=[location.latitude, location.longitude], zoom_start=15, tiles=map_style)
        folium.Marker(
            [location.latitude, location.longitude],
            tooltip=address_input,
            icon=folium.Icon(color="green" if within else "red", icon="home")
        ).add_to(m)

        folium.GeoJson(gdf.geometry, name="Kooyong Boundary").add_to(m)
        st_data = st_folium(m, width=1000, height=600)
