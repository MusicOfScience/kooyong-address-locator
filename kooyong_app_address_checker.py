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
    location = geocode_address(address_input)
    if location:
        folium.CircleMarker(
            location=(location.latitude, location.longitude),
            radius=8,
            color="red",
            fill=True,
            fill_color="red",
            fill_opacity=1
        ).add_to(m)

        try:
            tags = {"highway": True}
            nearby_streets = ox.features.geometries_from_point(
                (location.latitude, location.longitude),
                dist=100,
                tags=tags
            )
            ...
        except Exception as e:
            ...
    else:
        ...


# Optional street/suburb lookup table
with st.expander("🔍 Explore Kooyong Suburbs and Streets"):
    st.dataframe(lookup_df.rename(columns={
        "suburb": "Suburb",
        "street_name": "Street",
        "street_lower": "Street (lower)",
        "suburb_lower": "Suburb (lower)"
    }))
