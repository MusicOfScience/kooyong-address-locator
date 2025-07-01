import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from folium import Marker, GeoJson
from streamlit_folium import st_folium
from shapely.geometry import Point
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderUnavailable

# 📄 Page configuration
st.set_page_config(page_title="Kooyong Electorate Address Checker", layout="wide")
st.title("🗺️ Kooyong Streets with Suburb Lookup")

# 🔁 Cached loading functions
@st.cache_data
def load_kooyong_boundary():
    return gpd.read_file("E_VIC24_region.shp")

@st.cache_data
def load_street_data():
    return pd.read_csv("kooyong_street_suburb_lookup.csv")  # headers: suburb, street_name, street_lower, suburb_lower

@st.cache_data
def geocode_address(address):
    try:
        geolocator = Nominatim(user_agent="kooyong-locator")
        return geolocator.geocode(address)
    except GeocoderUnavailable:
        return None

# 🗺️ Load files
kooyong_gdf = load_kooyong_boundary()
street_df = load_street_data()

# 📥 User input
address_input = st.text_input("Enter an address (e.g., 145 Camberwell Road):")

# 🧠 Process and show result
if address_input:
    location = geocode_address(address_input)

    if not location:
        st.error("⚠️ Could not geocode the address.")
    else:
        point = Point(location.longitude, location.latitude)
        inside = kooyong_gdf.contains(point).any()

        if inside:
            st.success("✅ This address is within the Kooyong electorate.")
        else:
            st.warning("❌ This address is not within Kooyong.")

        # 🗺️ Start building map
        m = folium.Map(location=[location.latitude, location.longitude], zoom_start=16)

        # Draw Kooyong boundary
        folium.GeoJson(
            kooyong_gdf,
            name="Kooyong Boundary",
            style_function=lambda x: {
                "fillColor": "#00000000",
                "color": "#666666",
                "weight": 2,
                "dashArray": "5, 5"
            }
        ).add_to(m)

        # Find street name component from address
        words = address_input.lower().split()
        street_name = " ".join(w for w in words if w not in ['road', 'rd', 'street', 'st', 'avenue', 'ave'])
        matched = street_df[street_df['street_lower'].str.contains(street_name, na=False)]

        if not matched.empty:
            for _, row in matched.iterrows():
                match_str = f"{row['street_name']}, {row['suburb']}, VIC"
                segment_loc = geocode_address(match_str)
                if segment_loc:
                    seg_point = Point(segment_loc.longitude, segment_loc.latitude)
                    folium.CircleMarker(
                        location=[seg_point.y, seg_point.x],
                        radius=5,
                        color="#0CC0DF",
                        fill=True,
                        fill_color="#0CC0DF",
                        fill_opacity=0.7,
                        popup=f"{row['street_name']}, {row['suburb']}"
                    ).add_to(m)
        else:
            st.info("ℹ️ No matching street segment found in the dataset.")

        # Add red address pin
        Marker(
            location=[location.latitude, location.longitude],
            popup=address_input,
            icon=folium.Icon(color='red', icon='map-pin')
        ).add_to(m)

        # Show the final map
        st_folium(m, width=1200, height=600)
