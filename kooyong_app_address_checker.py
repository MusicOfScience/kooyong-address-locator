import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from shapely.geometry import Point
import re
import os

# Page config
st.set_page_config(
    page_title="Kooyong Address Checker",
    page_icon="🗺️",
    layout="wide"
)

# Title
st.title("🗺️ Kooyong Streets with Suburb Lookup")

@st.cache_data
def load_street_data():
    """Load the street lookup CSV"""
    try:
        df = pd.read_csv('kooyong_street_suburb_lookup.csv')
        return df
    except FileNotFoundError:
        st.error("❌ Could not find kooyong_street_suburb_lookup.csv")
        return None
    except Exception as e:
        st.error(f"❌ Error loading street data: {str(e)}")
        return None

@st.cache_data
def load_electorate_data():
    """Load and filter the shapefile for Kooyong electorate"""
    try:
        # Load the shapefile
        gdf = gpd.read_file('E_VIC24_region.shp')
        
        # Filter for Kooyong electorate
        kooyong = gdf[gdf['Elect_div'] == 'Kooyong']
        
        if kooyong.empty:
            st.error("❌ Kooyong electorate not found in shapefile")
            return None
            
        return kooyong
    except FileNotFoundError:
        st.error("❌ Could not find E_VIC24_region.shp shapefile")
        return None
    except Exception as e:
        st.error(f"❌ Error loading electorate data: {str(e)}")
        return None

def geocode_address(address):
    """Geocode an address to get lat/lon coordinates"""
    # 2024 Kooyong electorate suburbs (post-redistribution)
    kooyong_suburbs = [
        'Armadale', 'Canterbury', 'Deepdene', 'Hawthorn', 'Hawthorn East', 
        'Kew', 'Kew East', 'Kooyong', 'Malvern', 'Toorak',
        'Balwyn', 'Balwyn North', 'Camberwell', 'Glen Iris', 
        'Malvern East', 'Prahran', 'Surrey Hills'
    ]
    
    try:
        geolocator = Nominatim(user_agent="kooyong_address_checker")
        
        # Try geocoding the address as-is first
        location = geolocator.geocode(address, timeout=10)
        
        # If that fails, try adding likely Kooyong suburbs
        if not location:
            for suburb in kooyong_suburbs:
                enhanced_address = f"{address}, {suburb}, VIC, Australia"
                location = geolocator.geocode(enhanced_address, timeout=10)
                if location:
                    break
        
        # Final fallback to Melbourne
        if not location:
            enhanced_address = f"{address}, Melbourne, VIC, Australia"
            location = geolocator.geocode(enhanced_address, timeout=10)
        
        if location:
            return location.latitude, location.longitude, location.address
        else:
            return None, None, None
            
    except Exception as e:
        st.error(f"❌ Geocoding error: {str(e)}")
        return None, None, None

def parse_street_name(address):
    """Extract and normalize street name from address"""
    try:
        # Remove house numbers and normalize
        address_lower = address.lower().strip()
        
        # Remove leading numbers and common prefixes
        address_cleaned = re.sub(r'^\d+\s*', '', address_lower)
        address_cleaned = re.sub(r'^(unit|apt|apartment)\s*\d+[a-z]?\s*', '', address_cleaned)
        
        # Remove suburb names (anything after comma)
        if ',' in address_cleaned:
            address_cleaned = address_cleaned.split(',')[0].strip()
        
        return address_cleaned
        
    except Exception:
        return address.lower().strip()

def check_street_match(parsed_street, street_df):
    """Check if the parsed street matches any in the CSV"""
    if street_df is None:
        return False, None
    
    try:
        # Direct match in street_lower column
        matches = street_df[street_df['street_lower'].str.contains(parsed_street, case=False, na=False)]
        
        if not matches.empty:
            return True, matches.iloc[0]['street_name']
        
        # Fuzzy match - check if parsed street is contained in any street name
        fuzzy_matches = street_df[street_df['street_lower'].str.contains(
            parsed_street.split()[0] if parsed_street.split() else parsed_street, 
            case=False, na=False
        )]
        
        if not fuzzy_matches.empty:
            return True, fuzzy_matches.iloc[0]['street_name']
            
        return False, None
        
    except Exception:
        return False, None

def point_in_kooyong(lat, lon, kooyong_gdf):
    """Check if a point falls within Kooyong electorate"""
    if kooyong_gdf is None:
        return False
    
    try:
        point = Point(lon, lat)
        return kooyong_gdf.geometry.contains(point).any()
    except Exception:
        return False

def create_map(lat, lon, kooyong_gdf, address):
    """Create a Folium map with the address marker and Kooyong boundary"""
    try:
        # Create base map centered on the geocoded point
        m = folium.Map(
            location=[lat, lon],
            zoom_start=14,
            tiles='OpenStreetMap'
        )
        
        # Add marker for the address
        folium.Marker(
            [lat, lon],
            popup=f"📍 {address}",
            tooltip="Address Location"
        ).add_to(m)
        
        # Add Kooyong boundary if available
        if kooyong_gdf is not None:
            folium.GeoJson(
                kooyong_gdf.iloc[0].geometry,
                style_function=lambda x: {
                    'fillColor': 'lightblue',
                    'color': 'blue',
                    'weight': 2,
                    'fillOpacity': 0.3
                },
                popup="Kooyong Electorate",
                tooltip="Kooyong Electorate Boundary"
            ).add_to(m)
        
        return m
        
    except Exception as e:
        st.error(f"❌ Error creating map: {str(e)}")
        return None

# Main app logic
def main():
    # Load data
    street_df = load_street_data()
    kooyong_gdf = load_electorate_data()
    
    # Address input
    st.markdown("**Enter an address (e.g., 145 Camberwell Road):**")
    address_input = st.text_input("", placeholder="145 Camberwell Road")
    
    if st.button("🔍 Check Address") and address_input:
        with st.spinner("Geocoding address..."):
            # Step 1: Geocode the address
            lat, lon, full_address = geocode_address(address_input)
            
            if lat is None or lon is None:
                st.error("❌ Could not geocode the address. Please check the address and try again.")
                return
            
            st.success(f"📍 Geocoded to: {full_address}")
            
            # Step 2: Check if point is in Kooyong electorate
            in_kooyong = point_in_kooyong(lat, lon, kooyong_gdf)
            
            # Step 3: Check street match
            parsed_street = parse_street_name(address_input)
            street_match, matched_street_name = check_street_match(parsed_street, street_df)
            
            # Display results
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.subheader("📊 Results")
                
                if in_kooyong:
                    st.success("✅ This address is within the Kooyong electorate.")
                else:
                    st.error("❌ This address is NOT within the Kooyong electorate.")
                
                if street_match:
                    st.info(f"📍 Street segment matched: {matched_street_name}")
                else:
                    st.warning("🔍 No street match found in the lookup database.")
                
                # Display coordinates
                st.caption(f"Coordinates: {lat:.6f}, {lon:.6f}")
            
            with col2:
                st.subheader("🗺️ Map")
                
                # Create and display map
                map_obj = create_map(lat, lon, kooyong_gdf, address_input)
                if map_obj:
                    st_folium(map_obj, width=400, height=400)

    # File status check
    with st.expander("📁 Data File Status"):
        if os.path.exists('kooyong_street_suburb_lookup.csv'):
            st.success("✅ Street lookup CSV found")
        else:
            st.error("❌ kooyong_street_suburb_lookup.csv not found")
        
        if os.path.exists('E_VIC24_region.shp'):
            st.success("✅ Shapefile found")
        else:
            st.error("❌ E_VIC24_region.shp not found")

if __name__ == "__main__":
    main()
