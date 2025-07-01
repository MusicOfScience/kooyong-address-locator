# 📍 Kooyong Electorate Address Checker & Suburb Lookup

import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from shapely.geometry import Point, Polygon, MultiPolygon
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
import json
from datetime import datetime, timezone
import os
import time
import zipfile
import osmnx as ox

st.set_page_config(page_title="Kooyong Electorate Checker", layout="wide")
st.title("🗺️ Kooyong Streets with Suburb Lookup")

# ──────────────────────────────────────────────────────────────
# 📦 Load AEC Kooyong shapefile
@st.cache_data(show_spinner=False)
def load_kooyong_boundary():
    zip_path = "Vic-october-2024-esri.zip"
    extract_dir = "extracted_shapefiles"
    if not os.path.exists(extract_dir):
        os.makedirs(extract_dir)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)

    shp_file = None
    for root, _, files in os.walk(extract_dir):
        for f in files:
            if f.endswith(".shp") and "region" in f.lower():
                shp_file = os.path.join(root, f)
                break

    if not shp_file:
        st.error("❌ AEC shapefile not found.")
        return None

    gdf = gpd.read_file(shp_file)
    return gdf[gdf["Elect_div"] == "Kooyong"].to_crs(epsg=4326)

kooyong_gdf = load_kooyong_boundary()
kooyong_geom = kooyong_gdf.geometry.iloc[0] if kooyong_gdf is not None else None

# ──────────────────────────────────────────────────────────────
# 🧭 Load suburb lookup CSV
@st.cache_data(show_spinner=False)
def load_suburb_lookup():
    csv_path = "kooyong_street_suburb_lookup.csv"
    df = pd.read_csv(csv_path)
    df["street_lower"] = df["street"].str.lower()
    df["suburb"] = df["suburb"].str.title()
    return df

lookup_df = load_suburb_lookup()

# ──────────────────────────────────────────────────────────────
# 🚏 Get OSM road geometries inside Kooyong
def get_osm_street_geometries():
    tags = {"highway": True}
    gdf = ox.features_from_polygon(kooyong_geom, tags=tags)
    gdf = gdf[["geometry", "name"]].dropna(subset=["name"])
    gdf = gdf[gdf.geometry.geom_type.isin(["LineString", "MultiLineString"])]
    gdf["name_lower"] = gdf["name"].str.lower()
    return gdf

osm_streets = get_osm_street_geometries()

# ──────────────────────────────────────────────────────────────
# 🌐 Geocoder
def geocode_address(address, viewbox):
    geolocator = Nominatim(user_agent="kooyong_locator")
    try:
        location = geolocator.geocode(address, country_codes="au", addressdetails=True,
                                      viewbox=viewbox, bounded=True)
        return location
    except (GeocoderTimedOut, GeocoderUnavailable):
        return None

# ──────────────────────────────────────────────────────────────
# 🧾 Log queries
def log_geocode(input_query, result_type, latlon=None, suburb=None):
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": input_query,
        "result_type": result_type,
        "coords": latlon,
        "suburb": suburb,
    }
    with open("geocode_log.json", "a") as f:
        json.dump(record, f)
        f.write("\n")

# ──────────────────────────────────────────────────────────────
# 🗺️ Map setup
style = st.selectbox("Choose a map style:", [
    "OpenStreetMap", "CartoDB Positron", "CartoDB Dark_Matter", "Stamen Toner", "Stamen Terrain"
])

address = st.text_input("Enter a street address in Victoria:")

m = folium.Map(location=[-37.82, 145.05], zoom_start=13, tiles=style)

# Show Kooyong boundary
if kooyong_geom:
    folium.GeoJson(kooyong_geom, name="Kooyong", style_function=lambda x: {
        "fillColor": "#0cc0df", "color": "#190d51", "weight": 2, "fillOpacity": 0.1
    }).add_to(m)

# Show streets from OSM with suburb tooltips
for _, row in osm_streets.iterrows():
    match = lookup_df[lookup_df["street_lower"] == row["name_lower"]]
    tooltip = f"{row['name']}" if match.empty else f"{row['name']} → {match.iloc[0]['suburb']}"
    folium.GeoJson(row["geometry"], tooltip=tooltip,
                   style_function=lambda x: {"color": "#333", "weight": 2}).add_to(m)

# 📍 If address entered
if address.strip() and kooyong_geom:
    bounds = kooyong_geom.bounds
    viewbox = [[bounds[1], bounds[0]], [bounds[3], bounds[2]]]
    location = geocode_address(address, viewbox)
    if location:
        latlon = [location.latitude, location.longitude]
        point = Point(location.longitude, location.latitude)
        inside = kooyong_geom.contains(point)

        folium.Marker(latlon, tooltip="Your Address", icon=folium.Icon(color="blue")).add_to(m)

        st.success("✅ Inside Kooyong" if inside else "🚫 Outside Kooyong")
        log_geocode(address, "success", latlon, location.raw.get("address", {}).get("suburb"))
    else:
        st.warning("⚠️ Could not geocode address.")
        log_geocode(address, "fail")

st_folium(m, width=1000, height=600)
