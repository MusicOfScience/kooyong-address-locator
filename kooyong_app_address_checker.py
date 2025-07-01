import streamlit as st
import geopandas as gpd
import pandas as pd
import osmnx as ox
import matplotlib.pyplot as plt
from shapely.geometry import Point
from geopy.geocoders import Nominatim

st.set_page_config(page_title="Kooyong Streets with Suburb Lookup", layout="wide")

# ──────────────────────────────
# 📍 Geocode address function
@st.cache_data
def geocode_address(address):
    geolocator = Nominatim(user_agent="kooyong-locator")
    location = geolocator.geocode(address)
    return location

# ──────────────────────────────
# 📦 Load Kooyong boundary from shapefile
@st.cache_data
def load_kooyong_boundary():
    gdf = gpd.read_file("E_VIC24_region.shp")
    kooyong = gdf[gdf["Elect_div"] == "Kooyong"]
    return kooyong

# ──────────────────────────────
# 📄 Load street lookup CSV
@st.cache_data
def load_suburb_lookup():
    df = pd.read_csv("kooyong_street_suburb_lookup.csv")
    df["street_lower"] = df["street_name"].str.lower()
    df["suburb_lower"] = df["suburb"].str.lower()
    return df

# ──────────────────────────────
# 🛣️ Get OSM roads in Kooyong
@st.cache_data
def get_osm_roads_within_boundary(polygon):
    tags = {"highway": True}
    return ox.features_from_polygon(polygon, tags=tags)

# ──────────────────────────────
# 📍 UI + Lookup
st.title("🗺️ Kooyong Streets with Suburb Lookup")

address_input = st.text_input("Enter an address in Kooyong (e.g., '145 Camberwell Road')")

lookup_df = load_suburb_lookup()
kooyong_gdf = load_kooyong_boundary()
kooyong_polygon = kooyong_gdf.unary_union.convex_hull

if address_input:
    location = geocode_address(address_input)
    if location is None:
        st.error("⚠️ Could not geocode address.")
    else:
        address_point = Point(location.longitude, location.latitude)

        # Match street name
        matched_street = None
        for street in lookup_df["street_lower"].unique():
            if street in address_input.lower():
                matched_street = street
                break

        fig, ax = plt.subplots(figsize=(10, 10))
        kooyong_gdf.boundary.plot(ax=ax, color="black", linewidth=1)

        # Plot red dot at geocoded location
        ax.scatter(
            address_point.x,
            address_point.y,
            color="red",
            s=25,  # small dot
            label="Entered Address",
            zorder=5
        )

        # Highlight OSM roads inside Kooyong
        osm_gdf = get_osm_roads_within_boundary(kooyong_polygon)

        # If street match found, highlight it
        if matched_street:
            match = osm_gdf[osm_gdf["name"].str.lower().str.contains(matched_street, na=False)]
            if not match.empty:
                match.plot(ax=ax, color="#0CC0DF", alpha=0.7, linewidth=3, label="Matched Street")

        plt.axis("off")
        st.pyplot(fig)

        # Display matched suburb
        matched_rows = lookup_df[lookup_df["street_lower"] == matched_street]
        if not matched_rows.empty:
            st.success(f"✅ Suburb match: **{matched_rows.iloc[0]['suburb']}**")
        else:
            st.info("ℹ️ No exact suburb match found in lookup table.")
