# 🗺️ Kooyong Address Checker with OSM Streets and Suburb Overlay

import streamlit as st
import geopandas as gpd
import pandas as pd
import shapely.wkt
import folium
from shapely.geometry import Point, LineString, MultiLineString
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderUnavailable, GeocoderTimedOut
from datetime import datetime, timezone
import time
import json
import os
import zipfile

st.set_page_config(page_title="Kooyong Electorate Checker", layout="wide")
st.title("🗺️ Kooyong Streets with Suburb Lookup")

# --- Sidebar UI for map style ---
with st.sidebar:
    st.header("Map Settings")
    map_style = st.selectbox("Choose base map style:", [
        "OpenStreetMap", "Stamen Toner", "Stamen Terrain", "CartoDB Positron", "CartoDB Dark_Matter"])

# --- Address Input ---
address_input = st.text_input("Enter an address in Victoria (include suburb):")

# --- Street-to-suburb mapping (from Kooyong-specific CSV) ---
@st.cache_data(show_spinner=False)
def load_street_suburb_csv():
    csv_path = "kooyong_street_suburb_lookup.csv"
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        return df
    else:
        st.warning("CSV lookup file not found.")
        return pd.DataFrame()

# --- Load AEC Kooyong boundary shapefile ---
@st.cache_data(show_spinner=False)
def load_kooyong_boundary():
    zip_path = "Vic-october-2024-esri.zip"
    extract_dir = "extracted_aec"
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

    gdf = gpd.read_file(shp_file)
    kooyong = gdf[gdf["Elect_div"] == "Kooyong"].to_crs("EPSG:4326")
    return kooyong

# --- Geocoding logic ---
def enrich_query(query):
    default_suburb = "Kew"
    return f"{query}, {default_suburb}, VIC, Australia"

def get_kooyong_bounds(gdf):
    bounds = gdf.geometry.total_bounds
    return [bounds[0], bounds[1], bounds[2], bounds[3]]

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

def geocode_with_fallback(query, viewbox=None):
    geolocator = Nominatim(user_agent="kooyong_locator_app")
    time.sleep(1)
    try:
        location = geolocator.geocode(query, country_codes="au", addressdetails=True, viewbox=viewbox, bounded=True)
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

# --- Main ---
street_suburb_df = load_street_suburb_csv()
kooyong_gdf = load_kooyong_boundary()

if kooyong_gdf is not None:
    kooyong_poly_geom = kooyong_gdf.geometry.iloc[0]
    m = folium.Map(location=[-37.82, 145.05], zoom_start=14, tiles=map_style)

    # --- Overlay Kooyong boundary ---
    folium.GeoJson(kooyong_poly_geom, name="Kooyong Boundary").add_to(m)

    # --- Overlay OSM streets with tooltips ---
    for _, row in street_suburb_df.iterrows():
        if pd.notnull(row.get("geometry")):
            try:
                geo = shapely.wkt.loads(row["geometry"])
                if isinstance(geo, (LineString, MultiLineString)):
                    tooltip = f"{row['street_name']} → {row['suburb']}"
                    folium.GeoJson(geo, tooltip=tooltip).add_to(m)
            except Exception as e:
                continue

    # --- Geocode and add marker if address provided ---
    if address_input.strip():
        location, status = geocode_with_fallback(enrich_query(address_input), viewbox=get_kooyong_bounds(kooyong_gdf))
        if location:
            pt = Point(location.longitude, location.latitude)
            folium.Marker([location.latitude, location.longitude], tooltip="Your Address", icon=folium.Icon(color="blue")).add_to(m)
            within = kooyong_poly_geom.contains(pt)
            st.write("📍 Geocoded to:", location.latitude, location.longitude)
            st.write("🏘️ Suburb:", location.raw.get("address", {}).get("suburb", "Unknown"))
            if within:
                st.success("✅ Inside Kooyong")
            else:
                st.warning("🚫 Outside Kooyong")
        else:
            st.warning("⚠️ Could not geocode address.")

    st_folium(m, width=1000, height=600)
