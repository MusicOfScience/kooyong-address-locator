# 📍 Kooyong Electorate Address Checker (Streamlit App)

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

kooyong_suburbs = [
    "armadale", "balwyn", "balwyn north", "camberwell", "canterbury", "deepdene",
    "glen iris", "hawthorn", "hawthorn east", "kew", "kew east", "kooyong", "malvern",
    "malvern east", "mont albert", "mont albert north", "surrey hills", "toorak", "prahran"
]

def enrich_query(query):
    if not any(suburb in query.lower() for suburb in kooyong_suburbs):
        return f"{query}, Kew, VIC, Australia"
    return query

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
        st.error(f"❌ No .shp file found in {extract_dir}.")
        return None

    gdf = gpd.read_file(shp_file)
    if "Elect_div" not in gdf.columns:
        st.error("❌ 'Elect_div' column not found.")
        return None

    return gdf[gdf["Elect_div"] == "Kooyong"]

def get_kooyong_viewbox(gdf):
    try:
        bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
        return [bounds[0], bounds[1], bounds[2], bounds[3]]
    except Exception as e:
        st.warning("⚠️ Could not compute bounding box.")
        return None

def log_geocode_result(input_address, location, within, method="none", error=None):
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "input": input_address,
        "lat": location.latitude if location else None,
        "lon": location.longitude if location else None,
        "matched_suburb": location.raw.get("address", {}).get("suburb", "Unknown") if location else None,
        "in_kooyong": within,
        "method": method,
        "error": error
    }
    try:
        with open("geocode_log.json", "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except:
        pass

@lru_cache(maxsize=100)
def geocode_with_fallback(query, viewbox):
    geolocator = Nominatim(user_agent="kooyong_locator_app (https://github.com/MusicOfScience/kooyong-address-locator)")
    time.sleep(1)  # Rate-limit buffer
    try:
        location = geolocator.geocode(
            query,
            country_codes="au",
            addressdetails=True,
            viewbox=viewbox,
            bounded=True
        )
        if location:
            return location, "bounded"
    except:
        pass
    try:
        location = geolocator.geocode(
            query,
            country_codes="au",
            addressdetails=True
        )
        if location:
            return location, "unbounded"
    except:
        pass
    return None, "failed"

kooyong = load_kooyong_boundary()

if kooyong is not None and address_input.strip():
    viewbox = get_kooyong_viewbox(kooyong)

    if viewbox:
        query = enrich_query(address_input)
        location, method = geocode_with_fallback(query, viewbox)

        if location and location.raw.get("address", {}).get("state") == "Victoria":
            point = Point(location.longitude, location.latitude)
            within = kooyong.geometry.iloc[0].contains(point)

            st.write("📍 Geocoded to:", (location.latitude, location.longitude))
            st.write("📎 Full address:", location.raw.get("display_name"))
            st.write("🏘️ Suburb:", location.raw.get("address", {}).get("suburb", "Unknown"))
            st.write(f"🔎 Method used: `{method}`")

            if within:
                st.success("✅ This address is inside Kooyong.")
            else:
                st.warning("🚫 This address is outside Kooyong.")

            log_geocode_result(address_input, location, within, method=method)
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
            log_geocode_result(address_input, None, False, method=method, error="Not found or outside VIC")
    else:
        st.error("❌ Could not calculate Kooyong bounding box.")

