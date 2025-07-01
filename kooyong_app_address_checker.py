import streamlit as st
import geopandas as gpd
import pandas as pd
import osmnx as ox
import matplotlib.pyplot as plt
from shapely.geometry import Point
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderUnavailable

st.set_page_config(page_title="Kooyong Electorate Address Checker", layout="wide")
st.title("🗺️ Kooyong Streets with Suburb Lookup")

# ------------------------------
# 📍 Geocode address function
@st.cache_data
def geocode_address(address):
    geolocator = Nominatim(user_agent="kooyong-locator")
    try:
        location = geolocator.geocode(address)
        return location
    except GeocoderUnavailable:
        return None

# ------------------------------
# 🗂️ Load Vic shapefile for Kooyong
@st.cache_data
def load_kooyong_boundary():
    gdf = gpd.read_file("E_VIC24_region.shp")
    return gdf[gdf["Elect_div"] == "Kooyong"]

kooyong_gdf = load_kooyong_boundary()

# ------------------------------
# 📂 Load suburb/street CSV
@st.cache_data
def load_street_data():
    return pd.read_csv("kooyong_street_suburb_lookup.csv")  # expects headers: suburb, street_name, street_lower, suburb_lower

street_df = load_street_data()

# ------------------------------
# 🌐 Map style selector
map_style = st.selectbox("Choose a map style:", ["OpenStreetMap", "CartoDB positron", "Stamen Toner"])

# ------------------------------
# 🔍 Address input
address_input = st.text_input("Enter a street address in Victoria:")

if address_input:
    location = geocode_address(address_input)
    
    if location:
        address_point = Point(location.longitude, location.latitude)

        # Check if address is inside Kooyong
        in_kooyong = kooyong_gdf.geometry.unary_union.contains(address_point)

        # Filter street match
        address_words = address_input.lower().split()
        street_match = street_df[street_df['street_lower'].isin(address_words)]

        # Plot
        fig, ax = plt.subplots(figsize=(10, 10))
        kooyong_gdf.plot(ax=ax, color='lightgrey', edgecolor='black')

        # Highlight matching streets in teal with 70% opacity
        if not street_match.empty:
            match_streets = street_match['street_name'].str.lower().unique()
            tags = {'highway': True}
            osm_streets = ox.features_from_point((location.latitude, location.longitude), tags=tags, dist=300)
            if not osm_streets.empty:
                matched_osm = osm_streets[osm_streets['name'].str.lower().isin(match_streets)]
                if not matched_osm.empty:
                    matched_osm.plot(ax=ax, color='#0CC0DF', linewidth=3, alpha=0.7)

        # Red dot for location
        ax.scatter(location.longitude, location.latitude, color='red', s=25, zorder=5)

        ax.set_title(f"{address_input}\nIn Kooyong: {'✅ Yes' if in_kooyong else '❌ No'}", fontsize=14)
        ax.set_axis_off()
        st.pyplot(fig)
    else:
        st.error("⚠️ Could not geocode address.")
