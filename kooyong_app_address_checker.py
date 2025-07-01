import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from shapely.geometry import Point
from geopy.geocoders import Nominatim

# 📁 File paths
KOYONG_SHAPEFILE = "E_VIC24_region.shp"
LOOKUP_CSV = "kooyong_street_suburb_lookup.csv"

# 📦 Cached data loading
@st.cache_data
def load_kooyong_boundary():
    gdf = gpd.read_file(KOYONG_SHAPEFILE)
    return gdf[gdf['Elect_div'].str.lower() == 'kooyong'].to_crs(epsg=4326)

@st.cache_data
def load_street_data():
    return pd.read_csv(LOOKUP_CSV)

@st.cache_data
def geocode_address(address):
    geolocator = Nominatim(user_agent="kooyong_locator")
    location = geolocator.geocode(address)
    return location.latitude, location.longitude if location else (None, None)

# 🗺️ Load files
kooyong_gdf = load_kooyong_boundary()
street_df = load_street_data()

# 📥 User input
st.markdown("### 🗺️ Kooyong Streets with Suburb Lookup")
address_input = st.text_input("Enter an address (e.g., **145 Camberwell Road**):")

if address_input:
    # Geocode
    try:
        latitude, longitude = geocode_address(address_input)
    except:
        st.error("❌ Error geocoding address. Please check your input.")
        st.stop()

    # Electorate check
    point = Point(longitude, latitude)
    in_kooyong = kooyong_gdf.contains(point).any()

    if in_kooyong:
        st.success("✅ This address is within the Kooyong electorate.")
    else:
        st.error("❌ This address is not within Kooyong.")

    # Street match
    split_address = address_input.lower().split()
    match_row = None
    for _, row in street_df.iterrows():
        if all(part in row["street_lower"] for part in split_address if part.isalpha()):
            match_row = row
            break

    if match_row is not None:
        st.info(f"📍 Street segment matched: **{match_row['street_name']}**")
    else:
        st.warning("🔍 No matching street segment found in the dataset.")

    # Map
    m = folium.Map(location=[latitude, longitude], zoom_start=16)

    # Add electorate boundary
    folium.GeoJson(kooyong_gdf.geometry).add_to(m)

    # Add address marker (default pin to avoid broken icon)
    folium.Marker(
        location=[latitude, longitude],
        popup=address_input,
        tooltip="Exact address",
    ).add_to(m)

    # Render map
    st_data = st_folium(m, width=725)

