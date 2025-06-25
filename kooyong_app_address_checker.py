# 📍 Kooyong Address Checker & Map (Streamlit App)

import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from shapely.geometry import Point
from geopy.geocoders import Nominatim
import zipfile
import os

st.set_page_config(page_title="Kooyong Electorate Checker", layout="wide")

@st.cache_data
def load_kooyong_boundary():
    extract_dir = "data/aec_boundary"
    zip_path = "data/Vic-october-2024-esri.zip"

    if not os.path.exists(extract_dir):
        os.makedirs(extract_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

    shp_file = [f for f in os.listdir(extract_dir) if f.endswith(".shp")][0]
    gdf = gpd.read_file(os.path.join(extract_dir, shp_file))
    return gdf[gdf["Elect_div"].str.contains("Kooyong", case=False)]

@st.cache_data
def geocode_address(address):
    geolocator = Nominatim(user_agent="kooyong_locator")
    location = geolocator.geocode(address)
    return location.latitude, location.longitude if location else (None, None)

st.title("📍 Kooyong Electorate Address Checker")

address = st.text_input("Enter an address to check if it's in the Kooyong federal electorate:")

if address:
    try:
        lat, lon = geocode_address(address)
        if lat is None or lon is None:
            st.error("Could not geocode the address. Please try a more complete or accurate version.")
        else:
            user_point = Point(lon, lat)
            kooyong = load_kooyong_boundary()
            within = kooyong.contains(user_point).any()

            # ✅ FIXED: This block avoids the spooled object dump
            if within:
                st.success("✅ Inside Kooyong")
            else:
                st.warning("🚫 Outside Kooyong")

            # Map rendering
            m = folium.Map(location=[lat, lon], zoom_start=14)
            folium.Marker([lat, lon], tooltip="Your address").add_to(m)
            folium.GeoJson(kooyong.geometry).add_to(m)
            st_folium(m, width=800, height=500)

    except Exception as e:
        st.error(f"An error occurred: {e}")


