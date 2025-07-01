# 📍 Kooyong Electorate Address Checker – AEC-Boundary Powered

import streamlit as st
import geopandas as gpd
import folium
from shapely.geometry import Point
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderUnavailable
import zipfile
import os
import time
import json
from datetime import datetime
from functools import lru_cache

st.set_page_config(page_title="Kooyong Electorate Checker", layout="wide")
st.title("📍 Kooyong Electorate Address Checker")

style = st.selectbox("Choose a map style:", [
    "OpenStreetMap", "Stamen Toner", "Stamen Terrain", "CartoDB Positron", "CartoDB Dark_Matter"
])

address_input = st.text_input("Enter an address in Victoria:")

@st.cache_data(show_spinner=False)
def load_kooyong_boundary():
    zip_path = "Vic-october-2024-esri.zip"
    extract_dir = "extracted_shapefiles"

    if not os.path.exists(extract_dir):
        os.makedirs(extract_dir)

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
    except Exception as e:
        st.error("❌ Failed to extract shapefile.")
        return None

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

    return gdf[gdf["Elect_div"] == "Kooyong"]

def get_kooyong_viewbox(gdf):
    try:
        bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
        return [bounds[0], bounds[1], bounds[2], bounds[3]]  # [lon1, lat1, lon2, lat2]
    except Exception as e:
        st.warning("⚠️ Could not compute bounding box.")
        return None

def log_geocode_result(input_address, location, within, error=None):
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "input": input_address,
        "lat": location.latitude if location else None,
        "lon": location.longitude if location else None,
        "matched_suburb": location.raw.get("address", {}).get("suburb", "Unknown") if location else None,
        "in_kooyong": within,
        "error": error
    }
    try:
        with open("geocode_log.json", "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except:
        pass  # Fail silently for logging errors

@lru_cache(maxsize=100)
def safe_geocode(query, viewbox):
    try:
        time.sleep(1)
        geolocator = Nominatim(user_agent="kooyong_locator_app (https://github.com/MusicOfScience/kooyong-address-locator)")
        return geolocator.geocode(
            query,
            country_codes="au",
            addressdetails=True,
            viewbox=viewbox,
            bounded=True
        )
    except Exception:
        return None

kooyong = load_kooyong_boundary()

if kooyong is not None and address_input.strip():
    viewbox = get_kooyong_viewbox(kooyong)

    if viewbox:
        location = None
        try:
            location = safe_geocode(address_input, viewbox)
        except GeocoderUnavailable:
            st.error("⚠️ Geocoding temporarily unavailable.")
        except Exception as e:
            st.error("⚠️ Error during geocoding.")
            log_geocode_result(address_input, None, False, error=str(e))

        if location and location.raw.get("address", {}).get("state") == "Victoria":
            point = Point(location.longitude, location.latitude)
            within = kooyong.geometry.iloc[0].intersects(point)

            st.write("📍 Geocoded to:", (location.latitude, location.longitude))
            st.write("📎 Full address:", location.raw.get("display_name"))
            st.write("🏘️ Suburb:", location.raw.get("address", {}).get("suburb", "Unknown"))

            if within:
                st.success("✅ This address is inside Kooyong.")
            else:
                st.warning("🚫 This address is outside Kooyong.")

            log_geocode_result(address_input, location, within)

            m = folium.Map(location=[location.latitude, location.longitude], zoom_start=14, tiles=style)
            folium.Marker(
                [location.latitude, location.longitude],
                tooltip="Your address",
                icon=folium.Icon(color='blue')
            ).add_to(m)
            folium.GeoJson(kooyong.geometry.iloc[0], name="Kooyong Boundary").add_to(m)
            st_folium(m, width=1000, height=600)
        else:
            st.warning("⚠️ Address not found in Victoria, Australia.")
            log_geocode_result(address_input, None, False, error="Not found or outside Victoria")
    else:
        st.error("❌ Could not calculate Kooyong bounding box. Check shapefile.")
