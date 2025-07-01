import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from folium import Marker, GeoJson
from streamlit_folium import st_folium
from shapely.geometry import Point
from geopy.geocoders import Nominatim
import re

# 🔧 Setup
st.set_page_config(page_title="Kooyong Streets with Suburb Lookup", layout="wide")
st.title("🗺️ Kooyong Streets with Suburb Lookup")
st.markdown("Enter an address (e.g., **145 Camberwell Road**):")

# 📥 Input
address_input = st.text_input("", placeholder="145 Camberwell Road")

# 📦 Load Data
@st.cache_data
def load_kooyong_boundary():
    return gpd.read_file("E_VIC24_region.shp").to_crs(epsg=4326)

@st.cache_data
def load_street_data():
    return pd.read_csv("kooyong_street_suburb_lookup.csv")  # uses: street_lower, suburb_lower

# 🗂 Data
kooyong_gdf = load_kooyong_boundary()
street_df = load_street_data()

# 🧭 Geocode
@st.cache_data
def geocode_address(address):
    geolocator = Nominatim(user_agent="kooyong_app")
    return geolocator.geocode(address)

if address_input:
    location = geocode_address(address_input)
    if location:
        point = Point(location.longitude, location.latitude)
        address_geom = gpd.GeoDataFrame([{"geometry": point}], crs="EPSG:4326")

        # 🗳️ Check if in Kooyong
        in_kooyong = kooyong_gdf.contains(point).any()
        if in_kooyong:
            st.success("✅ This address is within the Kooyong electorate.")
        else:
            st.error("❌ This address is not within Kooyong.")

        # 🌐 Map
        map_center = [location.latitude, location.longitude]
        folium_map = folium.Map(location=map_center, zoom_start=16)

        # 📍 Pin
        Marker(location=[location.latitude, location.longitude], popup=address_input).add_to(folium_map)

        # 🔍 Match Street
        street_only = re.sub(r'^\d+\s*', '', address_input.lower())
        split_address = street_only.split()
        matched_row = None

        for _, row in street_df.iterrows():
            if all(part in row["street_lower"] for part in split_address):
                matched_row = row
                break

        if matched_row is not None:
            st.info(f"📌 Street segment matched: **{matched_row['street_name']}**")

            # Highlight matching street from OpenStreetMap (optional: requires .geojson)
            # If you have matching geometry, highlight it here

        else:
            st.warning("🔍 No matching street segment found in the dataset.")

        # 🗺️ Show Map
        st_folium(folium_map, use_container_width=True)
    else:
        st.error("⚠️ Address not found — please try a more specific format.")
