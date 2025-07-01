import streamlit as st
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderUnavailable

st.set_page_config(page_title="Kooyong Electorate Address Checker", layout="centered")

st.title("🗺️ Kooyong Streets with Suburb Lookup")
st.markdown("Check whether a street or address is within the **Kooyong electorate** boundaries using official 2024 data.")

# Load Kooyong boundary shapefile
@st.cache_data
def load_kooyong_boundary():
    gdf = gpd.read_file("E_VIC24_region.shp")
    gdf = gdf.to_crs("EPSG:4326")
    kooyong = gdf[gdf["Elect_div"] == "Kooyong"]
    return kooyong

kooyong_gdf = load_kooyong_boundary()

# Load street–suburb lookup CSV
@st.cache_data
def load_street_lookup():
    return pd.read_csv("kooyong_street_suburb_lookup.csv")

lookup_df = load_street_lookup()

# Choose map style
map_style = st.radio("Choose a map style:", ["OpenStreetMap", "CartoDB positron", "Stamen toner"])

# Address input
address_input = st.text_input("Enter a street address in Victoria:")

# Geocode and check if in Kooyong
if address_input:
    try:
        geolocator = Nominatim(user_agent="kooyong_checker")
        location = geolocator.geocode(f"{address_input}, Victoria, Australia", timeout=10)

        if location:
            address_point = Point(location.longitude, location.latitude)
            in_kooyong = kooyong_gdf.contains(address_point).any()

            st.map(pd.DataFrame({'lat': [location.latitude], 'lon': [location.longitude]}), zoom=16)

            st.success("✅ This address is **within Kooyong**." if in_kooyong else "❌ This address is **outside Kooyong**.")
        else:
            st.warning("⚠️ Could not geocode address.")
    except GeocoderUnavailable:
        st.error("⚠️ Geocoding service is temporarily unavailable.")
    except Exception as e:
        st.error(f"Error: {e}")

# Optional street/suburb lookup table
with st.expander("🔍 Explore Kooyong Suburbs and Streets"):
    st.dataframe(lookup_df.rename(columns={
        "suburb": "Suburb",
        "street_name": "Street",
        "street_lower": "Street (lower)",
        "suburb_lower": "Suburb (lower)"
    }))
