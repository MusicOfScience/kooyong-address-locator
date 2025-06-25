# 📍 Kooyong Address Checker & Map (Streamlit App)

import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from shapely.geometry import Point
from geopy.geocoders import Nominatim
import zipfile
import os

st.set_page_config(page_title="Kooyong Electorate Address Checker", layout="wide")

# Paths
ZIP_PATH = "data/Vic-october-2024-esri.zip"
EXTRACT_DIR = "data/aec_boundary"

@st.cache_data
def load_kooyong_boundary():
    # Check and extract shapefiles
    if not os.path.exists(EXTRACT_DIR):
        os.makedirs(EXTRACT_DIR, exist_ok=True)
        with zipfile.ZipFile(ZIP_PATH, "r") as zip_ref:
            zip_ref.extractall(EXTRACT_DIR)

    # Find the .shp file
    shp_files = [f for f in os.listdir(EXTRACT_DIR) if f.endswith(".shp")]
    if not shp_files:
        return None

    # Load and filter for Kooyong
    gdf = gpd.read_file(os.path.join(EXTRACT_DIR, shp_files[0]))
    return gdf[gdf["Elect_div"].str.contains("Kooyong", case=False)]

@st.cache_data
def geocode_address(address):
    geolocator = Nominatim(user_agent="kooyong_locator")
    location = geolocator.geocode(address)
    return (location.latitude, location.longitude) if location else (None, None)

st.title("📍 Kooyong Electorate Address Checker")

address = st.text_input("Enter a Victorian address to check if it’s inside the Kooyong federal electorate:")

if address:
    lat, lon = geocode_address(address)
    if lat is None or lon is None:
        st.error("❌ Could not locate that address. Try a more specific or complete version.")
    else:
        kooyong = load_kooyong_boundary()
        if kooyong is None:
            st.error("❌ Could not load Kooyong shapefile. Ensure the ZIP is uploaded correctly.")
        else:
            point = Point(lon, lat)
            within = kooyong.contains(point).any()

            if within:
                st.success("✅ This address is inside the Kooyong electorate.")
            else:
                st.warning("🚫 This address is outside the Kooyong electorate.")

            # 🌐 Show map
            m = folium.Map(location=[lat, lon], zoom_start=14, tiles="CartoDB Positron")
            folium.Marker([lat, lon], tooltip="📍 Your address").add_to(m)
            folium.GeoJson(kooyong.geometry, name="Kooyong Boundary").add_to(m)
            st_folium(m, width=800, height=500)



