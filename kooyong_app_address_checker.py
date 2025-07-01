import streamlit as st
import geopandas as gpd
import osmnx as ox
import pandas as pd
import shapely
from shapely.geometry import Point
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Kooyong Streets with Suburb Lookup", layout="wide")

# ──────────────────────────────
# Load Kooyong AEC Boundary from ESRI Shapefile
# ──────────────────────────────

@st.cache_data
def load_kooyong_boundary():
    gdf = gpd.read_file("Vic-october-2024-esri.zip")
    gdf = gdf.to_crs(epsg=4326)  # Ensure consistent CRS
    kooyong_gdf = gdf[gdf["Elect_div"].str.upper() == "KOOYONG"]
    return kooyong_gdf

kooyong_gdf = load_kooyong_boundary()
kooyong_geom = kooyong_gdf.unary_union

# ──────────────────────────────
# Download OSM street geometries inside Kooyong boundary
# ──────────────────────────────

@st.cache_data
def get_osm_street_geometries(_polygon):
    tags = {"highway": True}
    streets = ox.geometries_from_polygon(_polygon, tags=tags)
    return streets

osm_streets = get_osm_street_geometries(kooyong_geom)

# ──────────────────────────────
# Extract and clean street names
# ──────────────────────────────

@st.cache_data
def extract_unique_street_names(streets):
    name_col = "name"
    if name_col not in streets.columns:
        return []
    names = streets[name_col].dropna().unique()
    return sorted(names)

street_names = extract_unique_street_names(osm_streets)

# ──────────────────────────────
# Sidebar UI
# ──────────────────────────────

st.sidebar.header("🗺️ Kooyong Street & Suburb Lookup")
street_input = st.sidebar.selectbox("Select a street in Kooyong:", street_names)

# ──────────────────────────────
# Filter for selected street
# ──────────────────────────────

selected = osm_streets[osm_streets["name"] == street_input]

# ──────────────────────────────
# Map Display
# ──────────────────────────────

m = folium.Map(location=[-37.82, 145.05], zoom_start=14)

# Show Kooyong boundary
folium.GeoJson(kooyong_gdf.geometry.iloc[0], name="Kooyong Boundary", style_function=lambda x: {
    "fillColor": "#0CC0DF", "color": "#190D51", "weight": 2, "fillOpacity": 0.1
}).add_to(m)

# Add selected street
for _, row in selected.iterrows():
    geom = row.geometry
    if isinstance(geom, shapely.geometry.LineString):
        folium.PolyLine(locations=[(pt[1], pt[0]) for pt in geom.coords], color="red").add_to(m)
    elif isinstance(geom, shapely.geometry.MultiLineString):
        for line in geom:
            folium.PolyLine(locations=[(pt[1], pt[0]) for pt in line.coords], color="red").add_to(m)

# Show map
st_data = st_folium(m, width=1000, height=600)

# ──────────────────────────────
# Display Suburb Info (if available)
# ──────────────────────────────

if "addr:suburb" in selected.columns:
    suburbs = selected["addr:suburb"].dropna().unique()
    if len(suburbs):
        st.info(f"📍 This street is located in: **{', '.join(suburbs)}**.")
    else:
        st.warning("No suburb information found in OpenStreetMap data.")
else:
    st.warning("No `addr:suburb` column found in OSM data.")
