# 📍 Kooyong Address Checker & Map (Streamlit App)

import streamlit as st
import zipfile
import os
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from shapely.geometry import Point
from geopy.geocoders import Nominatim
import tempfile

st.set_page_config(page_title="Kooyong Address Checker", layout="wide")

# 🎨 Custom theme
st.markdown("""
    <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        .css-1d391kg {padding: 2rem 1rem 10rem;}
    </style>
""", unsafe_allow_html=True)

st.title("📍 Kooyong Electorate Address Checker (2025)")

@st.cache_data(show_spinner=False)
def extract_and_load_shapefile():
    shapefile_dir = "Data/Vic-october-2024-esri"
    if not os.path.exists(shapefile_dir):
        raise FileNotFoundError("❌ Kooyong shapefile directory not found.")
    shp_files = [f for f in os.listdir(shapefile_dir) if f.endswith(".shp")]
    if not shp_files:
        raise FileNotFoundError(f"❌ No .shp files found in {shapefile_dir}. Contents: {os.listdir(shapefile_dir)}")
    shp_path = os.path.join(shapefile_dir, shp_files[0])
    gdf = gpd.read_file(shp_path)
    return gdf

@st.cache_data(show_spinner=False)
def get_geolocator():
    return Nominatim(user_agent="kooyong-checker")

# 🔽 Style selector
style = st.selectbox("Choose a map style:", ["OpenStreetMap", "Stamen Toner", "CartoDB Positron"], index=0)

# 📬 Address input
address_input = st.text_input("Enter an address in Victoria:", "123 High St, Kew")

if address_input:
    geolocator = get_geolocator()
    try:
        location = geolocator.geocode(address_input, country_codes="au", exactly_one=True, timeout=10)
    except Exception as e:
        st.error("🌐 Geocoding service is temporarily unavailable. Please try again later.")
        st.stop()

    if not location:
        st.warning("⚠️ Could not geocode that address. Please try a more specific or local address.")
        st.stop()

    point = Point(location.longitude, location.latitude)
    try:
        gdf = extract_and_load_shapefile()
    except Exception as e:
        st.error("❌ Could not load Kooyong shapefile. Ensure the ZIP is uploaded correctly.")
        st.stop()

    within = gdf.contains(point).any()

    if within:
        st.success("✅ Inside Kooyong")
    else:
        st.warning("🚫 Outside Kooyong")

    # 🗺️ Map drawing
    m = folium.Map(location=[location.latitude, location.longitude], zoom_start=14, tiles=style)
    folium.Marker([location.latitude, location.longitude], popup="Your address").add_to(m)
    folium.GeoJson(gdf.geometry, name="Kooyong Boundary", style_function=lambda x: {
        'fillColor': '#00B4B6', 'color': '#005566', 'weight': 2, 'fillOpacity': 0.2
    }).add_to(m)

    st_folium(m, width=1000, height=600)


