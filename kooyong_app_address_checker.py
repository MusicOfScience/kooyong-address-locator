# 📍 Kooyong Address Checker & Map (Streamlit App)

import streamlit as st
import geopandas as gpd
import osmnx as ox
import contextily as ctx
import matplotlib.pyplot as plt
from shapely.geometry import Point
from geopy.geocoders import Nominatim
from io import BytesIO

# --- SETUP ---
st.set_page_config(page_title="Kooyong 2025 Map", layout="wide")
st.title("🗺️ Kooyong 2025 Map with Address Checker")
st.caption("Check if an address is inside Kooyong and generate a stylised map.")

# --- LOAD BOUNDARY ---
@st.cache_data
def load_kooyong_boundary():
    url = "https://github.com/MusicOfScience/kooyong-maps/raw/main/FED__2024_Electoral_Divisions.shp.zip"
    gdf = gpd.read_file(f"zip://{url}!")
    kooyong = gdf[gdf["Elect_div"].str.contains("Kooyong", case=False)]
    return kooyong.to_crs(epsg=3857)

kooyong = load_kooyong_boundary()

# --- SIDEBAR ---
st.sidebar.header("📮 Address Lookup")
address = st.sidebar.text_input("Enter an address", value="25 Smith St, Hawthorn VIC")
style = st.sidebar.selectbox("🗺️ Basemap style", [
    "OpenStreetMap.Mapnik",
    "CartoDB.Positron",
    "CartoDB.DarkMatter",
    "Stamen.TonerLite",
])

# --- GEOCODING ---
geolocator = Nominatim(user_agent="kooyong_checker")
location = geolocator.geocode(address)
gpoint = None

if location:
    lon, lat = location.longitude, location.latitude
    point = Point(lon, lat)
    gpoint = gpd.GeoDataFrame(geometry=[point], crs="EPSG:4326").to_crs(epsg=3857)
    inside = kooyong.contains(gpoint.geometry.iloc[0]).bool()
    result_msg = "✅ Inside Kooyong" if inside else "❌ Outside Kooyong"
else:
    result_msg = "❌ Could not geocode address"

# --- DISPLAY RESULT ---
st.subheader("📍 Address Check Result")
st.markdown(f"**{address}** → {result_msg}")

# --- PLOT MAP ---
fig, ax = plt.subplots(figsize=(12, 8))
ctx.add_basemap(ax, source=eval(f"ctx.providers.{style}"))
kooyong.boundary.plot(ax=ax, edgecolor="#00e0d6", linewidth=2)

if gpoint is not None:
    gpoint.plot(ax=ax, color="red", markersize=100)
    ax.text(
        gpoint.geometry.x.iloc[0],
        gpoint.geometry.y.iloc[0] + 100,
        "📍 Your Address",
        fontsize=10,
        ha="center",
        color="red"
    )

ax.axis('off')
st.pyplot(fig)

# --- DOWNLOAD ---
buf = BytesIO()
fig.savefig(buf, format="png", dpi=300, bbox_inches="tight")
st.download_button("📥 Download map as PNG", data=buf.getvalue(), file_name="kooyong_map.png", mime="image/png")
