# 📍 Kooyong Address Checker & Map (Streamlit App)

import streamlit as st
import geopandas as gpd
import folium
from shapely.geometry import Point
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderUnavailable
import zipfile
import os

st.set_page_config(page_title="Kooyong Electorate Checker", layout="wide")
st.title("📍 Kooyong Electorate Address Checker")

# 🎨 MAP STYLE SELECTOR
style = st.selectbox("Choose a map style:", [
    "OpenStreetMap", "Stamen Toner", "Stamen Terrain", "CartoDB Positron", "CartoDB Dark_Matter"
])

# 📮 ADDRESS INPUT
address_input = st.text_input("Enter an address in Victoria:")

@st.cache_data(show_spinner=False)
def load_kooyong_boundary():
    zip_path = "Vic-october-2024-esri.zip"  # 🧠 Removed the 'Data/' folder assumption
    extract_dir = "extracted_shapefiles"

    if not os.path.exists(extract_dir):
        os.makedirs(extract_dir)

    # Extract ZIP
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)

   
    # Find .shp inside nested folders
    shp_file = None
    for root, dirs, files in os.walk(extract_dir):
        for f in files:
            if f.endswith(".shp"):
                shp_file = os.path.join(root, f)
                break

    if not shp_file:
        st.error(f"❌ No .shp file found in {extract_dir}.")
        return None

    gdf = gpd.read_file(shp_file)

    if "Elect_div" not in gdf.columns:
        st.error("❌ 'Elect_div' column not found in shapefile.")
        return None

    kooyong = gdf[gdf["Elect_div"] == "Kooyong"]
    return kooyong

kooyong = load_kooyong_boundary()

# 🧭 GEOCODE AND CHECK
if kooyong is not None and address_input.strip():
    geolocator = Nominatim(user_agent="kooyong_locator")

    try:
        location = geolocator.geocode(
            address_input,
            country_codes="au",
            addressdetails=True,
        )
    except GeocoderUnavailable:
        st.error("⚠️ Geocoding temporarily unavailable.")
        location = None

    if location and location.raw.get("address", {}).get("state") == "Victoria":
        point = Point(location.longitude, location.latitude)
        within = kooyong.geometry.iloc[0].contains(point)

        if within:
            st.success("✅ Inside Kooyong")
        else:
            st.warning("🚫 Outside Kooyong")

        # 🗺️ FOLIUM MAP
        m = folium.Map(location=[location.latitude, location.longitude], zoom_start=14, tiles=style)
        folium.Marker([location.latitude, location.longitude], tooltip="Your address", icon=folium.Icon(color='blue')).add_to(m)
        folium.GeoJson(kooyong.geometry.iloc[0], name="Kooyong Boundary").add_to(m)

        st_folium(m, width=1000, height=600)␊
    else:␊
        st.warning("⚠️ Address not found in Victoria, Australia.")
