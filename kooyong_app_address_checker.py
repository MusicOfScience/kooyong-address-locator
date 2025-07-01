import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from folium import GeoJson, Marker
from streamlit_folium import st_folium
from shapely.geometry import Point
from geopy.geocoders import Nominatim

# ----------------------
# 🎯 Load datasets
# ----------------------
@st.cache_data
def load_kooyong_boundary():
    return gpd.read_file("E_VIC24_region.shp")

@st.cache_data
def load_street_data():
    return pd.read_csv("kooyong_street_suburb_lookup.csv")  # use correct file name

@st.cache_data
def geocode_address(address):
    geolocator = Nominatim(user_agent="kooyong-locator")
    location = geolocator.geocode(address)
    return location

# ----------------------
# 🌏 App layout
# ----------------------
st.title("🗺️ Kooyong Streets with Suburb Lookup")
address_input = st.text_input("Enter an address (e.g., 145 Camberwell Road):")

kooyong_gdf = load_kooyong_boundary()
street_df = load_street_data()

if address_input:
    location = geocode_address(address_input)
    if location:
        point = Point(location.longitude, location.latitude)
        in_kooyong = kooyong_gdf.contains(point).any()

        # ✅ Display Kooyong status
        if in_kooyong:
            st.success("✅ This address is within the Kooyong electorate.")
        else:
            st.error("❌ This address is not within Kooyong.")

        # 🗺️ Map setup
        map_center = [location.latitude, location.longitude]
        m = folium.Map(location=map_center, zoom_start=16)

        # 🔵 Drop pin
        Marker(map_center, tooltip="Entered Address").add_to(m)

        # --------------------------
        # 🧠 Match street from input
        # --------------------------
        split_address = address_input.lower().split()
        matched_row = None

        for _, row in street_df.iterrows():
            if all(part in row["street_lower"] for part in split_address):
                matched_row = row
                break

        if matched_row is not None:
            st.info(f"📍 Matched Street Segment: **{matched_row['street_name']}**, {matched_row['suburb']}")
            matched_street = matched_row["street_lower"]

            # ✅ Highlight matching street in teal
            def style_function(feature):
                name = feature["properties"].get("FULL_NAME", "").lower()
                if matched_street in name:
                    return {"color": "#0CC0DF", "weight": 5}
                else:
                    return {"color": "#888888", "weight": 1, "opacity": 0.2}

            GeoJson(kooyong_gdf, style_function=style_function).add_to(m)

        else:
            st.warning("🔍 No matching street segment found in the dataset.")

        # 🔽 Show map
        st_folium(m, width=725, height=500)
    else:
        st.error("📍 Could not geocode this address.")
