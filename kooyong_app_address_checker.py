# 📍 Kooyong Address Checker & Map (Streamlit App)

import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from shapely.geometry import Point
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderUnavailable

import zipfile
import os

st.set_page_config(page_title="Kooyong Address Checker", layout="wide")

st.title("📍 Kooyong Electorate Address Checker")

# --- STYLE SELECTOR ---
style = st.selectbox("Choose a map style:", [
    "OpenStreetMap", "Stamen Toner", "Stamen Terrain", "CartoDB Positron", "CartoDB Dark_Matter"
])

# --- ADDRESS INPUT ---
address_input = st.text_input("Enter an address in Victoria:")

@st.cache_data(show_spinner=False)
def load_kooyong_boundary():
    extract_dir = "extracted_shapefiles/Vic-october-2024-esri"
    shp_file = "E_VIC24_region.shp"
    shp_path = os.path.join(extract_dir, shp_file)

    if not os.path.exists(shp_path):
        st.error("❌ Could not load Kooyong shapefile. Ensure the ZIP is uploaded correctly.")
        return None

    gdf = gpd.read_file(shp_path)
    kooyong = gdf[gdf["Elect_div"] == "Kooyong"]
    return kooyong

kooyong = load_kooyong_boundary()

if kooyong is not None and address_input.strip():
    geolocator = Nominatim(user_agent="kooyong_locator")

    try:
        location = geolocator.geocode(address_input)
    except GeocoderUnavailable:
        st.error("⚠️ Geocoding service temporarily unavailable.")
        location = None

    if location:
        point = Point(location.longitude, location.latitude)
        within = kooyong.geometry.iloc[0].contains(point)

        # Display user-friendly message
        if within:
            st.success("✅ Inside Kooyong")
        else:
            st.warning("🚫 Outside Kooyong")

        # --- CREATE MAP ---
        m = folium.Map(location=[location.latitude, location.longitude], zoom_start=14, tiles=style)
        folium.Marker([location.latitude, location.longitude], tooltip="Your address", icon=folium.Icon(color='blue')).add_to(m)
        folium.GeoJson(kooyong.geometry.iloc[0], name="Kooyong Boundary").add_to(m)

        st_folium(m, width=1000, height=600)
    else:
        st.warning("⚠️ Could not find that address. Try a more specific location.")
