# 📍 Kooyong Address Checker & Map (Streamlit App)

import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import zipfile
import os

# --- CONFIG ---
ZIP_PATH = "data/Vic-october-2024-esri.zip"
EXTRACT_DIR = "extracted_shapefiles"

# --- LOAD BOUNDARY ---
@st.cache_data
def load_kooyong_boundary():
    if not os.path.exists(EXTRACT_DIR):
        os.makedirs(EXTRACT_DIR, exist_ok=True)
        with zipfile.ZipFile(ZIP_PATH, "r") as zip_ref:
            zip_ref.extractall(EXTRACT_DIR)

    shp_files = [f for f in os.listdir(EXTRACT_DIR) if f.endswith(".shp")]
    if not shp_files:
        st.error(f"❌ No .shp files found in {EXTRACT_DIR}. Contents: {os.listdir(EXTRACT_DIR)}")
        return None

    gdf = gpd.read_file(os.path.join(EXTRACT_DIR, shp_files[0]))
    return gdf[gdf["Elect_div"].str.contains("Kooyong", case=False)]

# --- GEOCODE ---
from geopy.geocoders import Nominatim
geolocator = Nominatim(user_agent="kooyong_checker")

def geocode_address(address):
    try:
        location = geolocator.geocode(address + ", Victoria, Australia", timeout=10)
        if location:
            return location.latitude, location.longitude
    except Exception:
        pass
    return None, None

# --- APP ---
st.set_page_config(layout="wide", page_title="Kooyong Boundary Checker 🗺️")
st.title("🗳️ Kooyong Electorate Boundary Checker")

address = st.text_input("📮 Enter an address in Victoria:", "123 High St, Kew")
lat, lon = geocode_address(address)

gdf = load_kooyong_boundary()
if gdf is None:
    st.stop()

if lat is not None and lon is not None:
    point = gpd.points_from_xy([lon], [lat], crs="EPSG:4326")
    within = gdf.to_crs("EPSG:4326").contains(point[0])

    # ✅ Show ONLY the message — suppress all extra object details
    if within:
        st.success("✅ Inside Kooyong")
    else:
        st.warning("🚫 Outside Kooyong")

    # --- DRAW MAP ---
    m = folium.Map(location=[lat, lon], zoom_start=14, control_scale=True)
    folium.Marker(location=[lat, lon], popup="Entered Address", icon=folium.Icon(color="red")).add_to(m)
    folium.GeoJson(gdf).add_to(m)
    st_folium(m, width=900, height=600)

else:
    st.error("Could not geocode the address. Try again with more detail.")
