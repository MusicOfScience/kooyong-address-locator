import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from folium import Marker, GeoJson
from streamlit_folium import st_folium
from shapely.geometry import Point
from geopy.geocoders import Nominatim

# 🌐 Page config
st.set_page_config(page_title="Kooyong Streets with Suburb Lookup", layout="wide")

# 🎨 Styling
st.markdown("""
    <style>
        .title { font-size: 40px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# 🗂️ Load Kooyong boundary shapefile (in EPSG:4326)
@st.cache_data
def load_kooyong_boundary():
    return gpd.read_file("E_VIC24_region.shp").to_crs("EPSG:4326")

# 🛣️ Load local street/suburb lookup CSV
@st.cache_data
def load_street_lookup():
    return pd.read_csv("kooyong_street_suburb_lookup.csv")  # headers: street, suburb

# 🛣️ Load road geometries shapefile (e.g., Vicmap or equivalent)
@st.cache_data
def load_road_geometries():
    return gpd.read_file("E_VIC24_region.shp").to_crs("EPSG:4326")

# 📍 Geocode address to lat/lon
@st.cache_data
def geocode_address(address):
    geolocator = Nominatim(user_agent="kooyong-locator")
    location = geolocator.geocode(address)
    return location

# 🔄 Load data
kooyong_gdf = load_kooyong_boundary()
road_gdf = load_road_geometries()
street_lookup = load_street_lookup()

# 📥 User input
address_input = st.text_input("Enter an address (e.g., 145 Camberwell Road):")

# 🧠 Process
if address_input:
    location = geocode_address(address_input)
    
    if location is None:
        st.error("❌ Could not geocode the address.")
    else:
        point = Point(location.longitude, location.latitude)
        in_kooyong = kooyong_gdf.contains(point).any()

        # ✔️ Kooyong indicator
        if in_kooyong:
            st.success("✅ This address is within the Kooyong electorate.")
        else:
            st.error("❌ This address is not within Kooyong.")

        # 🔍 Extract street name from address
        split_address = address_input.lower().replace(",", "").split()
        matched_row = None
        for idx, row in street_lookup.iterrows():
            if all(part in row["street"].lower() for part in split_address):
                matched_row = row
                break

        # 🗺️ Create map
        m = folium.Map(location=[location.latitude, location.longitude], zoom_start=16)
        Marker(location=[location.latitude, location.longitude], tooltip=address_input).add_to(m)

        if matched_row is not None:
            st.subheader(f"Matched Street Segment: {matched_row['street']}, {matched_row['suburb']}")

            # Filter for matching road segment
            road_match = road_gdf[road_gdf["V_NAME"].str.lower().str.contains(matched_row["street"].lower())]

            if not road_match.empty:
                GeoJson(
                    road_match,
                    name="Matched Street",
                    style_function=lambda x: {
                        "color": "#0CC0DF",  # teal highlight
                        "weight": 5
                    }
                ).add_to(m)
            else:
                st.info("ℹ️ No matching road geometry found in shapefile.")
        else:
            st.warning("⚠️ No matching street segment found in the dataset.")

        st_folium(m, width=800, height=600)
