import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from folium import Marker, GeoJson
from streamlit_folium import st_folium
from shapely.geometry import Point
from geopy.geocoders import Nominatim

# ------------------------------
# 📍 Page configuration
st.set_page_config(
    page_title="Kooyong Streets with Suburb Lookup",
    layout="wide",
)

st.title("📍 Kooyong Streets with Suburb Lookup")

# ------------------------------
# 🗺️ Map style selector
map_tile = st.selectbox("Choose a map style:", ["OpenStreetMap", "CartoDB positron", "Stamen Terrain"])

# ------------------------------
# 📂 Load shapefile
@st.cache_data
def load_shapefile():
    return gpd.read_file("E_VIC24_region.shp")

kooyong_gdf = load_shapefile()

# ------------------------------
# 📂 Load street/suburb CSV
@st.cache_data
def load_street_data():
    return pd.read_csv("kooyong_street_suburb_lookup.csv")  # expects: suburb, street_name, street_lower, suburb_lower

street_df = load_street_data()

# ------------------------------
# 📍 Geocoding function
@st.cache_data
def geocode_address(address):
    geolocator = Nominatim(user_agent="kooyong-locator")
    return geolocator.geocode(address)

# ------------------------------
# 🧠 Helper: Check point in Kooyong
def is_in_kooyong(point):
    return kooyong_gdf.contains(point).any()

# ------------------------------
# 📍 Address input
address_input = st.text_input("Enter a street address in Victoria:", placeholder="e.g. 145 Camberwell Road, Hawthorn East")

if address_input:
    location = geocode_address(f"{address_input}, Victoria, Australia")
    if location:
        point = Point(location.longitude, location.latitude)
        in_kooyong = is_in_kooyong(point)

        # 🗺️ Create map
        m = folium.Map(location=[location.latitude, location.longitude], zoom_start=16, tiles=map_tile)

        # 🟦 Add Kooyong boundary
        GeoJson(
            kooyong_gdf.geometry,
            name="Kooyong Boundary",
            style_function=lambda x: {"fillColor": "#00000000", "color": "#0CC0DF", "weight": 2}
        ).add_to(m)

        # 📍 Add marker
        Marker(
            location=[location.latitude, location.longitude],
            popup=location.address,
            icon=folium.Icon(color='lightblue', icon='map-marker', prefix='fa')
        ).add_to(m)

        # 🧵 Attempt to highlight road
        try:
            import osmnx as ox
            road = ox.features_from_point(
                (location.latitude, location.longitude),
                tags={"highway": True},
                dist=80
            )
            if not road.empty:
                gdf = gpd.GeoDataFrame(road, crs="EPSG:4326")
                GeoJson(
                    gdf.geometry,
                    name="Highlighted Road",
                    style_function=lambda x: {
                        "color": "#0CC0DF",
                        "weight": 4,
                        "opacity": 0.7
                    }
                ).add_to(m)
        except Exception as e:
            st.warning(f"Could not highlight road segment: {e}")

        # 🖼️ Render map
        st.markdown(f"### {address_input}")
        st.markdown(f"**In Kooyong:** {'✅ Yes' if in_kooyong else '❌ No'}")
        st_data = st_folium(m, width=1000, height=600)

    else:
        st.error("Could not geocode the address. Please try a more complete address (include suburb).")
