import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from folium import Marker, GeoJson
from streamlit_folium import st_folium
from shapely.geometry import Point
from geopy.geocoders import Nominatim
import matplotlib.pyplot as plt

# ------------------------------
# 🧭 Page Config
st.set_page_config(page_title="Kooyong Streets with Suburb Lookup", layout="centered")
st.title("🗺️ Kooyong Streets with Suburb Lookup")

# ------------------------------
# 📂 Load suburb/street CSV
@st.cache_data
def load_street_data():
    return pd.read_csv("kooyong_street_suburb_lookup.csv")  # Expects headers: suburb, street_name, street_lower, suburb_lower

street_df = load_street_data()

# ------------------------------
# 📍 Geocode address function
@st.cache_data
def geocode_address(address):
    geolocator = Nominatim(user_agent="kooyong-locator")
    location = geolocator.geocode(address)
    return location

# ------------------------------
# 🗺️ Load Kooyong shapefile
@st.cache_data
def load_kooyong_shape():
    return gpd.read_file("E_VIC24_region.shp")

kooyong_shape = load_kooyong_shape()
kooyong_shape = kooyong_shape.to_crs(epsg=4326)  # Ensure it's in lat/lon for folium

# ------------------------------
# 🌐 Map style selector
map_style = st.selectbox("Choose a map style:", ["OpenStreetMap", "CartoDB Positron", "Stamen Toner", "Stamen Terrain"])

# ------------------------------
# 🧾 Address Input
address_input = st.text_input("Enter a street address in Victoria:", "")

if address_input:
    address = address_input.strip()
    location = geocode_address(address + ", Victoria, Australia")

    if location:
        point_geom = Point(location.longitude, location.latitude)
        is_in_kooyong = kooyong_shape.contains(point_geom).any()

        # Match with lookup table
        address_lower = address.lower()
        matching_row = street_df[street_df['street_lower'].apply(lambda x: x in address_lower)]

        suburb_display = matching_row['suburb'].values[0] if not matching_row.empty else "Unknown suburb"

        st.markdown(f"### {address_input}<br>In Kooyong: {'✅ Yes' if is_in_kooyong else '❌ No'}", unsafe_allow_html=True)

        # ------------------------------
        # 🗺️ Map setup
        folium_map = folium.Map(location=[location.latitude, location.longitude], zoom_start=15, tiles=map_style)

        # 🟦 Kooyong shape in teal with 70% opacity
        GeoJson(
            kooyong_shape,
            name="Kooyong Boundary",
            style_function=lambda feature: {
                "fillColor": "#0CC0DF",
                "color": "#0CC0DF",
                "weight": 2,
                "fillOpacity": 0.7,
            }
        ).add_to(folium_map)

        # 🔴 Address Marker (small pin-like marker)
        Marker(
            location=[location.latitude, location.longitude],
            icon=folium.Icon(color='red', icon='map-pin', prefix='fa')
        ).add_to(folium_map)

        # 🖼️ Display map
        st_data = st_folium(folium_map, width=700, height=500)

    else:
        st.error("Address not found. Please try again with more detail (e.g. include suburb or number).")
