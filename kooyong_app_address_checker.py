import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
import osmnx as ox
from shapely.geometry import Polygon, Point
from geopy.geocoders import Nominatim

st.set_page_config(page_title="Kooyong Streets with Suburb Lookup", layout="wide")
st.title("🗺️ Kooyong Streets with Suburb Lookup")

# ──────────────────────────────
# Load Kooyong street-suburb CSV
# ──────────────────────────────
@st.cache_data
def load_suburb_lookup():
    df = pd.read_csv("kooyong_street_suburb_lookup.csv")
    df["street_lower"] = df["street_name"].str.lower()
    df["suburb"] = df["suburb"].str.title()
    return df

lookup_df = load_suburb_lookup()

# ──────────────────────────────────────────────
# Define Kooyong boundary manually or dynamically
# ──────────────────────────────────────────────
@st.cache_data
def get_kooyong_geometry():
    kooyong_suburbs = [
        "Kew", "Kew East", "Balwyn", "Balwyn North", "Deepdene", "Canterbury",
        "Camberwell", "Surrey Hills", "Mont Albert", "Mont Albert North",
        "Malvern", "Malvern East", "Toorak", "Armadale", "Glen Iris", "Prahran"
    ]
    gdf = ox.geocode_to_gdf([f"{suburb}, Victoria, Australia" for suburb in kooyong_suburbs])
    return gdf.unary_union.convex_hull

kooyong_geom = get_kooyong_geometry()

# ──────────────────────────────
# Load OSM street geometries
# ──────────────────────────────
@st.cache_data
def get_osm_street_geometries(polygon):
    tags = {"highway": True}
    return ox.geometries_from_polygon(polygon, tags)

osm_streets = get_osm_street_geometries(kooyong_geom)

# ──────────────────────────────
# Create base map with street tooltips
# ──────────────────────────────
def generate_map():
    center = [kooyong_geom.centroid.y, kooyong_geom.centroid.x]
    fmap = folium.Map(location=center, zoom_start=14, tiles=st.selectbox("Choose a map style:", [
        "OpenStreetMap", "Stamen Toner", "CartoDB positron", "CartoDB dark_matter"
    ]))

    for _, row in lookup_df.iterrows():
        matches = osm_streets[osm_streets["name"].str.lower() == row["street_lower"]]
        for _, match in matches.iterrows():
            geom = match.geometry
            if geom.geom_type == "LineString":
                folium.PolyLine(locations=[(pt[1], pt[0]) for pt in geom.coords],
                                tooltip=f'{row["street_name"]} — {row["suburb"]}',
                                color="blue", weight=3).add_to(fmap)

    return fmap

st_data = st_folium(generate_map(), width=1000, height=600)

# ──────────────────────────────
# Address lookup box
# ──────────────────────────────
user_input = st.text_input("Enter a street address in Victoria:")
if user_input:
    geolocator = Nominatim(user_agent="kooyong_locator")
    location = geolocator.geocode(f"{user_input}, Victoria, Australia")
    if location:
        point = Point(location.longitude, location.latitude)
        st.success(f"📍 Found: {location.address}")
        st.map(pd.DataFrame({'lat': [location.latitude], 'lon': [location.longitude]}))
        if kooyong_geom.contains(point):
            st.info("✅ This address is **within Kooyong**.")
        else:
            st.warning("⚠️ This address is **outside Kooyong**.")
    else:
        st.error("⚠️ Could not geocode address.")
