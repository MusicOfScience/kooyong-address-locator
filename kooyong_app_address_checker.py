# 📍 Kooyong Electorate Address Checker & Map (Streamlit)

import streamlit as st
import geopandas as gpd
import folium
from shapely.geometry import Point
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderUnavailable, GeocoderTimedOut
from datetime import datetime, timezone
import time
import zipfile
import os
import json

st.set_page_config(page_title="Kooyong Electorate Checker", layout="wide")
st.title("📍 Kooyong Electorate Address Checker")

# 🗺️ Choose map style
style = st.selectbox("Choose a map style:", [
    "OpenStreetMap", "Stamen Toner", "Stamen Terrain", "CartoDB Positron", "CartoDB Dark_Matter"
])

# 📮 User input
address_input = st.text_input("Enter an address in Victoria (include street & suburb for better accuracy):")

# 📦 Smart enrichment map: street name → correct Kooyong suburb
street_suburb_map = {
    "munro street": "balwyn",
    "camberwell road": "hawthorn east",
    "manningtree road": "canterbury",
    "wattle valley road": "canterbury",
    "toorak road": "malvern",
    "union road": "surrey hills",
    "mont albert road": "mont albert",
    "cotham road": "kew",
    "glenferrie road": "kew",
    "barkers road": "kew",
    "glen iris road": "glen iris",
    "balwyn road": "balwyn",
    "canterbury road": "canterbury"
}

# 📥 Enrich vague queries with known Kooyong suburb
def enrich_query(query):
    q_lower = query.lower()
    for street, suburb in street_suburb_map.items():
        if street in q_lower:
            return f"{query}, {suburb.title()}, VIC, Australia"
    return f"{query}, Kew, VIC, Australia"

# ⛳ Load Kooyong AEC boundary shapefile
@st.cache_data(show_spinner=False)
def load_kooyong_boundary():
    zip_path = "Vic-october-2024-esri.zip"
    extract_dir = "extracted_shapefiles"
    if not os.path.exists(extract_dir):
        os.makedirs(extract_dir)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)

    shp_file = None
    for root, dirs, files in os.walk(extract_dir):
        for f in files:
            if f.endswith(".shp"):
                shp_file = os.path.join(root, f)
                break

    if not shp_file:
        st.error("❌ No .shp file found.")
        return None

    gdf = gpd.read_file(shp_file)
    if "Elect_div" not in gdf.columns:
        st.error("❌ 'Elect_div' column missing in shapefile.")
        return None

    kooyong = gdf[gdf["Elect_div"] == "Kooyong"]
    return kooyong

kooyong = load_kooyong_boundary()

# 🎯 Get Kooyong bounding box from AEC polygon
def get_kooyong_bounds(gdf):
    try:
        bounds = gdf.geometry.total_bounds  # [minx, miny, maxx, maxy]
        return [bounds[0], bounds[1], bounds[2], bounds[3]]
    except Exception as e:
        st.warning(f"⚠️ Failed to derive bounding box: {e}")
        return [145.00, -37.85, 145.08, -37.80]

# 🌐 Smart geocoder with logging
def geocode_with_fallback(query, viewbox=None):
    geolocator = Nominatim(user_agent="kooyong_locator_app (https://github.com/MusicOfScience/kooyong-address-locator)")
    time.sleep(1)

    try:
        location = geolocator.geocode(
            query,
            country_codes="au",
            addressdetails=True,
            viewbox=viewbox,
            bounded=True
        )
    except (GeocoderUnavailable, GeocoderTimedOut) as e:
        log_geocode(query, None, None, "timeout", str(e))
        return None, "timeout"
    except Exception as e:
        log_geocode(query, None, None, "error", str(e))
        return None, "error"

    if location:
        suburb = location.raw.get("address", {}).get("suburb", "Unknown")
        log_geocode(query, location, suburb, "success")
        return location, "success"
    else:
        log_geocode(query, None, None, "not_found")
        return None, "not_found"

# 🧾 Log to JSON
def log_geocode(input_query, location, suburb, result_type, error_msg=None):
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input": input_query,
        "result_type": result_type,
        "suburb": suburb,
        "coords": [location.latitude, location.longitude] if location else None,
        "error": error_msg
    }
    with open("geocode_log.json", "a") as f:
        json.dump(record, f)
        f.write("\n")

# 🧭 Main logic
if kooyong is not None and address_input.strip():
    viewbox = get_kooyong_bounds(kooyong)
    query = enrich_query(address_input)

    location, method = geocode_with_fallback(query, viewbox)
    if not location:
        st.warning("⚠️ Address not found in Victoria, Australia.")
    else:
        st.write("📦 Using bounding box:", viewbox)
        st.write("📍 Geocoded to:", location.latitude, location.longitude)
        st.write("🏘️ Suburb:", location.raw.get("address", {}).get("suburb", "Unknown"))

        point = Point(location.longitude, location.latitude)
        within = kooyong.geometry.iloc[0].contains(point)

        if within:
            st.success("✅ Inside Kooyong")
        else:
            st.warning("🚫 Outside Kooyong")

        m = folium.Map(location=[location.latitude, location.longitude], zoom_start=15, tiles=style)
        folium.Marker(
            [location.latitude, location.longitude],
            tooltip="Your address",
            icon=folium.Icon(color='blue')
        ).add_to(m)
        folium.GeoJson(kooyong.geometry.iloc[0], name="Kooyong Boundary").add_to(m)

        st_folium(m, width=1000, height=600)
