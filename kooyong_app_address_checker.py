# 📍 Kooyong Address Checker & Map (Streamlit App)

import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import folium_static
from shapely.geometry import Point
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
import zipfile
import os
import time

st.set_page_config(page_title="Kooyong Address Checker", layout="wide")

st.title("📍 Kooyong Electorate Address Checker")

# 🎯 Load Kooyong shapefile from ZIP in ./Data
@st.cache_data
def load_kooyong_boundary():
    zip_path = "Data/Vic-october-2024-esri.zip"
    extract_dir = "extracted_shapefiles"

    if not os.path.exists(extract_dir):
        os.makedirs(extract_dir)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_dir)

    shapefiles = []
    for root, _, files in os.walk(extract_dir):
        for file in files:
            if file.endswith(".shp"):
                shapefiles.append(os.path.join(root, file))

    if not shapefiles:
        raise FileNotFoundError(f"❌ No .shp files found in {extract_dir}. Contents: {os.listdir(extract_dir)}")

    gdf = gpd.read_file(shapefiles[0])
    return gdf.to_crs(epsg=4326)

# 🧭 Load map styles
map_styles = {
    "OpenStreetMap": "OpenStreetMap",
    "CartoDB Positron": "CartoDB Positron",
    "Stamen Toner Lite": "Stamen TonerLite",
}

# 📮 User input
address_input = st.text_input("Enter an address in Victoria:")

style = st.selectbox("Choose a map style:", list(map_styles.keys()))

# 📦 Load boundary
try:
    kooyong = load_kooyong_boundary()
except Exception as e:
    st.error("❌ Could not load Kooyong shapefile. Ensure the ZIP is uploaded correctly.")
    st.stop()

# 📌 Geocode
if address_input:
    geolocator = Nominatim(user_agent="kooyong-checker")
    try:
        location = geolocator.geocode(address_input, timeout=10)
        time.sleep(1.5)  # avoid over-querying
    except (GeocoderTimedOut, GeocoderUnavailable):
        st.error("🌐 Geocoder is unavailable. Please wait or try again.")
        st.stop()
    except Exception as e:
        st.error(f"❌ Unexpected error: {e}")
        st.stop()

    if not location:
        st.warning("❓ Address not found. Check for typos or try a full address.")
        st.stop()

    point = Point(location.longitude, location.latitude)
    within = kooyong.contains(point).any()

    # ✅ Inside/outside message only
    if within:
        st.success("✅ This address is within Kooyong.")
    else:
        st.warning("🚫 This address is outside Kooyong.")

    # 🗺️ Map
    m = folium.Map(location=[location.latitude, location.longitude], zoom_start=14, tiles=map_styles[style])

    folium.GeoJson(kooyong.geometry, name="Kooyong Boundary").add_to(m)
    folium.Marker(
        [location.latitude, location.longitude],
        popup=f"You entered: {address_input}",
        icon=folium.Icon(color="blue" if within else "red", icon="map-marker")
    ).add_to(m)

    folium_static(m)
