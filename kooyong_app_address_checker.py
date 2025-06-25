# 📍 Kooyong Address Checker & Map (Streamlit App)

import streamlit as st
import geopandas as gpd
import zipfile, os
import matplotlib.pyplot as plt
from shapely.geometry import Point
from geopy.geocoders import Nominatim

st.set_page_config(page_title="Kooyong Boundary Checker", layout="wide")

@st.cache_data(show_spinner="Loading Kooyong boundaries…")
def load_kooyong_boundary():
    local_zip = "data/Vic-october-2024-esri.zip"
    extract_dir = "/tmp/aec_data"

    if not os.path.exists(extract_dir):
        with zipfile.ZipFile(local_zip, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

    shp_file = [f for f in os.listdir(extract_dir) if f.endswith(".shp")][0]
    full_path = os.path.join(extract_dir, shp_file)

    gdf = gpd.read_file(full_path)
    return gdf[gdf["Elect_div"].str.contains("Kooyong", case=False)].to_crs(epsg=3857)

def geocode_address(address):
    geolocator = Nominatim(user_agent="kooyong-checker")
    try:
        location = geolocator.geocode(address)
        if location:
            return Point(location.longitude, location.latitude)
    except:
        return None
    return None

st.title("📮 Kooyong 2025 Boundary Checker")

address = st.text_input("Enter an address (e.g. '385 Toorak Rd, South Yarra')")

gdf = load_kooyong_boundary()

if address:
    point = geocode_address(address)
    if point:
        projected_point = gpd.GeoSeries([point], crs="EPSG:4326").to_crs(gdf.crs)
        inside = gdf.contains(projected_point.iloc[0]).any()
        status = "✅ Inside Kooyong" if inside else "❌ Outside Kooyong"
        st.subheader(status)

        fig, ax = plt.subplots(figsize=(10, 10))
        gdf.plot(ax=ax, color="white", edgecolor="black")
        projected_point.plot(ax=ax, color="red", markersize=50)
        ax.set_title("Kooyong Boundary with Address Point")
        st.pyplot(fig)
    else:
        st.error("Address could not be geocoded.")

