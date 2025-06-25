# 📍 Kooyong Address Checker & Map (Streamlit App)

import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
import zipfile
import os
import shutil

# 📍 CONFIG
st.set_page_config(page_title="Kooyong Address Checker", layout="wide")

# 📦 Load shapefile from ZIP
@st.cache_resource
def load_kooyong_boundary():
    zip_path = "data/Vic-october-2024-esri.zip"
    extract_dir = "data/aec_extracted"

    # Clean and extract
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)

    # 🔍 Find the .shp file recursively
    shp_file = None
    for root, _, files in os.walk(extract_dir):
        for f in files:
            if f.endswith(".shp"):
                shp_file = os.path.join(root, f)
                break
        if shp_file:
            break

    # 🚨 Handle failure
    if not shp_file:
        st.error("Shapefile not found inside the ZIP archive.")
        return None

    gdf = gpd.read_file(shp_file)
    kooyong = gdf[gdf["Elect_div"].str.contains("Kooyong", case=False)]
    return kooyong

# 🗺️ Create base map
def create_map(kooyong_gdf, style_choice):
    centroid = kooyong_gdf.geometry.centroid.iloc[0]
    m = folium.Map(location=[centroid.y, centroid.x], zoom_start=13, tiles=style_choice)

    # 🎨 Boundary polygon
    folium.GeoJson(kooyong_gdf.geometry,
                   name="Kooyong",
                   style_function=lambda x: {
                       'fillColor': '#b0f0ea',
                       'color': '#00B4B6',
                       'weight': 3,
                       'fillOpacity': 0.1
                   }).add_to(m)
    return m

# 🔍 Geocode address
def geocode_address(address):
    try:
        from geopy.geocoders import Nominatim
        geolocator = Nominatim(user_agent="kooyong_checker")
        location = geolocator.geocode(address)
        if location:
            return (location.latitude, location.longitude)
        else:
            return None
    except Exception as e:
        st.error(f"Geocoding error: {e}")
        return None

# 🚀 MAIN APP
st.title("📮 Kooyong Address Checker")
st.markdown("Check whether an address is within the **2025 Kooyong federal electorate boundary**.")

kooyong_gdf = load_kooyong_boundary()
if kooyong_gdf is None:
    st.stop()

# 🌈 Map style
style_choice = st.selectbox("🗺 Choose map style", [
    "CartoDB positron",
    "OpenStreetMap",
    "Stamen Toner",
    "Stamen Terrain"
])

# 📮 Address input
address = st.text_input("Enter an address in Kooyong (e.g., 123 Glenferrie Rd, Kew VIC)")

if address:
    coords = geocode_address(address)
    if coords:
        point = gpd.GeoDataFrame(geometry=gpd.points_from_xy([coords[1]], [coords[0]]), crs="EPSG:4326")
        within = point.within(kooyong_gdf.unary_union).iloc[0]

        st.success("✅ Inside Kooyong") if within else st.warning("🚫 Outside Kooyong")

        # 📍 Show map
        m = create_map(kooyong_gdf, style_choice)
        folium.Marker(location=coords, popup=address, icon=folium.Icon(color="blue")).add_to(m)
        st_data = st_folium(m, width=700, height=500)

    else:
        st.error("Couldn't locate that address.")

