# kooyong_app_address_checker.py

import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from shapely.geometry import Point
from streamlit_folium import st_folium
import osmnx as ox
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

st.set_page_config(page_title="Kooyong Address Checker", layout="wide")
st.title("🗺️ Kooyong Streets with Suburb Lookup")

# ──────────────────────────────
# Load and prep street-suburb data
# ──────────────────────────────

@st.cache_data
def load_street_lookup():
    df = pd.read_csv("kooyong_street_suburb_lookup.csv")
    df["street_lower"] = df["street_lower"].str.strip().str.lower()
    df["suburb_lower"] = df["suburb_lower"].str.strip().str.lower()
    return df

lookup_df = load_street_lookup()

# ──────────────────────────────
# Load Kooyong boundary
# ──────────────────────────────

@st.cache_data
def load_kooyong_boundary():
    gdf = gpd.read_file("kooyong_boundary.geojson")
    return gdf.unary_union.convex_hull  # returns a shapely Polygon

kooyong_geom = load_kooyong_boundary()

# ──────────────────────────────
# Download OSM street geometries
# ──────────────────────────────

@st.cache_data
def get_osm_street_geometries(_polygon):
    tags = {"highway": True}
    return ox.geometries_from_polygon(_polygon, tags)

osm_streets = get_osm_street_geometries(kooyong_geom)

# ──────────────────────────────
# Sidebar interface
# ──────────────────────────────

st.sidebar.subheader("Choose a map style:")
tiles = st.sidebar.radio("Map tiles", ["OpenStreetMap", "CartoDB positron", "Stamen Toner"])

st.sidebar.subheader("Enter a street address in Victoria:")
address_input = st.sidebar.text_input("E.g. 145 Camberwell Road")

# ──────────────────────────────
# Geocode address if provided
# ──────────────────────────────

if address_input:
    geolocator = Nominatim(user_agent="kooyong-checker")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

    location = geocode(address_input + ", VIC, Australia")
    if location:
        address_point = Point(location.longitude, location.latitude)
        inside_kooyong = kooyong_geom.contains(address_point)
        address_result = f"✅ Located at ({location.latitude:.5f}, {location.longitude:.5f})"
        if inside_kooyong:
            address_result += " and is *within Kooyong*."
        else:
            address_result += " and is *outside Kooyong*."
        st.sidebar.markdown(address_result)
    else:
        st.sidebar.error("⚠️ Could not geocode address.")

# ──────────────────────────────
# Build folium map
# ──────────────────────────────

m = folium.Map(location=[-37.82, 145.05], zoom_start=13, tiles=tiles)

# Add Kooyong boundary
folium.GeoJson(kooyong_geom, name="Kooyong", tooltip="Kooyong Boundary").add_to(m)

# Add street name tooltips
for idx, row in osm_streets.iterrows():
    if row.geometry.geom_type in ["LineString", "MultiLineString"]:
        name = row.get("name", None)
        if name:
            folium.GeoJson(
                row.geometry,
                tooltip=f"{name}",
                style_function=lambda x: {"color": "#007AFF", "weight": 2},
            ).add_to(m)

# ──────────────────────────────
# Overlay tooltip data from our CSV
# ──────────────────────────────

with st.expander("View all known street–suburb matches in Kooyong"):
    st.dataframe(lookup_df[["street_name", "suburb"]].sort_values(by="street_name").drop_duplicates())

# ──────────────────────────────
# Display map
# ──────────────────────────────

st_folium(m, width=1000, height=600)

