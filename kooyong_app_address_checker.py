\import streamlit as st
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

def geocode_address(address, street_df=None):
    """Geocode an address to get lat/lon coordinates with improved logic"""
    # 2024 Kooyong electorate suburbs (post-redistribution)
    kooyong_suburbs = [
        'Armadale', 'Canterbury', 'Deepdene', 'Hawthorn', 'Hawthorn East', 
        'Kew', 'Kew East', 'Kooyong', 'Malvern', 'Toorak',
        'Balwyn', 'Balwyn North', 'Camberwell', 'Glen Iris', 
        'Malvern East', 'Prahran', 'Surrey Hills'
    ]
    
    try:
        geolocator = Nominatim(user_agent="kooyong_address_checker")
        best_result = None
        
        # Parse street name to see if we can match it in our database first
        parsed_street = parse_street_name(address)
        matching_suburbs = []
        
        if street_df is not None:
            matches = street_df[street_df['street_lower'].str.contains(parsed_street, case=False, na=False)]
            if not matches.empty:
                matching_suburbs = matches['suburb'].unique().tolist()
        
        # Strategy 1: If we found matching suburbs in our database, try those first
        if matching_suburbs:
            st.info(f"🔍 Found '{parsed_street}' in suburbs: {', '.join(matching_suburbs)}")
            for suburb in matching_suburbs:
                if suburb in kooyong_suburbs:  # Only try Kooyong suburbs
                    enhanced_address = f"{address}, {suburb}, VIC, Australia"
                    location = geolocator.geocode(enhanced_address, timeout=10)
                    if location:
                        return location.latitude, location.longitude, location.address, f"Matched via database suburb: {suburb}"
        
        # Strategy 2: Try with each Kooyong suburb
        for suburb in kooyong_suburbs:
            enhanced_address = f"{address}, {suburb}, VIC, Australia"
            location = geolocator.geocode(enhanced_address, timeout=10)
            if location:
                # Check if the returned address actually contains the Kooyong suburb
                if any(ks.lower() in location.address.lower() for ks in kooyong_suburbs):
                    return location.latitude, location.longitude, location.address, f"Matched with Kooyong suburb: {suburb}"
                else:
                    # Store as backup but keep looking
                    if best_result is None:
                        best_result = (location.latitude, location.longitude, location.address, f"Backup result from: {suburb}")
        
        # Strategy 3: Try with VIC, Australia (general Victoria search)
        location = geolocator.geocode(f"{address}, VIC, Australia", timeout=10)
        if location:
            # Check if it's in a Kooyong suburb
            if any(ks.lower() in location.address.lower() for ks in kooyong_suburbs):
                return location.latitude, location.longitude, location.address, "Matched via VIC search"
            else:
                if best_result is None:
                    best_result = (location.latitude, location.longitude, location.address, "VIC general search")
        
        # Strategy 4: Try with Melbourne, VIC, Australia
        location = geolocator.geocode(f"{address}, Melbourne, VIC, Australia", timeout=10)
        if location:
            if any(ks.lower() in location.address.lower() for ks in kooyong_suburbs):
                return location.latitude, location.longitude, location.address, "Matched via Melbourne search"
            else:
                if best_result is None:
                    best_result = (location.latitude, location.longitude, location.address, "Melbourne general search")
        
        # Strategy 5: Last resort - address as-is
        location = geolocator.geocode(address, timeout=10)
        if location:
            if any(ks.lower() in location.address.lower() for ks in kooyong_suburbs):
                return location.latitude, location.longitude, location.address, "Matched via direct search"
            else:
                if best_result is None:
                    best_result = (location.latitude, location.longitude, location.address, "Direct search")
        
        # Return best result if we have one, even if not ideal
        if best_result:
            return best_result[0], best_result[1], best_result[2], f"{best_result[3]} (may not be in Kooyong)"
        
        return None, None, None, None
            
    except Exception as e:
        st.error(f"❌ Geocoding error: {str(e)}")
        return None, None, None, None

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
    """Check if the parsed street matches any in the CSV and return all matches"""
    if street_df is None:
        return False, None, []
    
    try:
        # Direct match in street_lower column
        matches = street_df[street_df['street_lower'].str.contains(parsed_street, case=False, na=False)]
        
        if not matches.empty:
            # Return all matching suburbs for this street
            suburbs_list = matches[['street_name', 'suburb']].to_dict('records')
            return True, matches.iloc[0]['street_name'], suburbs_list
        
        # Fuzzy match - check if parsed street is contained in any street name
        fuzzy_matches = street_df[street_df['street_lower'].str.contains(
            parsed_street.split()[0] if parsed_street.split() else parsed_street, 
            case=False, na=False
        )]
        
        if not fuzzy_matches.empty:
            suburbs_list = fuzzy_matches[['street_name', 'suburb']].to_dict('records')
            return True, fuzzy_matches.iloc[0]['street_name'], suburbs_list
            
        return False, None, []
        
    except Exception:
        return False, None, []

def point_in_kooyong(lat, lon, kooyong_gdf):
    """Check if a point falls within Kooyong electorate"""
    if kooyong_gdf is None:
        return False
    
    try:
        point = Point(lon, lat)
        return kooyong_gdf.geometry.contains(point).any()
    except Exception:
        return False

def create_map(lat, lon, kooyong_gdf, address, in_kooyong):
    """Create a Folium map with the address marker and Kooyong boundary"""
    try:
        # Create base map centered on the geocoded point
        m = folium.Map(
            location=[lat, lon],
            zoom_start=14,
            tiles='OpenStreetMap'
        )
        
        # Choose marker color based on whether it's in Kooyong
        marker_color = 'green' if in_kooyong else 'red'
        marker_icon = 'ok' if in_kooyong else 'remove'
        
        # Add marker for the address
        folium.Marker(
            [lat, lon],
            popup=f"📍 {address}",
            tooltip="Address Location",
            icon=folium.Icon(color=marker_color, icon=marker_icon)
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
    # Initialize session state to preserve results
    if 'results' not in st.session_state:
        st.session_state.results = None
    
    # Load data
    street_df = load_street_data()
    kooyong_gdf = load_electorate_data()
    
    # Address input
    st.markdown("**Enter an address (e.g., 145 Camberwell Road or just Munro Street):**")
    address_input = st.text_input(
        "Address", 
        placeholder="145 Camberwell Road or Munro Street",
        label_visibility="hidden"
    )
    
    # Add helpful tips
    st.info("💡 **Tips:** Include house number for best results. If searching just a street name, the app will try to find it within Kooyong suburbs first.")
    
    if st.button("🔍 Check Address") and address_input:
        with st.spinner("Geocoding address..."):
            # Step 1: Geocode the address (now with improved logic)
            lat, lon, full_address, search_method = geocode_address(address_input, street_df)
            
            if lat is None or lon is None:
                st.error("❌ Could not geocode the address. Please check the address and try again.")
                st.session_state.results = None
                return
            
            # Step 2: Check if point is in Kooyong electorate
            in_kooyong = point_in_kooyong(lat, lon, kooyong_gdf)
            
            # Step 3: Check street match
            parsed_street = parse_street_name(address_input)
            street_match, matched_street_name, matching_suburbs = check_street_match(parsed_street, street_df)
            
            # Store results in session state
            st.session_state.results = {
                'address_input': address_input,
                'lat': lat,
                'lon': lon,
                'full_address': full_address,
                'search_method': search_method,
                'in_kooyong': in_kooyong,
                'street_match': street_match,
                'matched_street_name': matched_street_name,
                'matching_suburbs': matching_suburbs,
                'kooyong_gdf': kooyong_gdf
            }
    
    # Display results if they exist
    if st.session_state.results:
        results = st.session_state.results
        
        st.success(f"📍 Geocoded to: {results['full_address']}")
        if results['search_method']:
            st.caption(f"Search method: {results['search_method']}")
        
        # Display results
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("📊 Results")
            
            if results['in_kooyong']:
                st.success("✅ This address is within the Kooyong electorate.")
            else:
                st.error("❌ This address is NOT within the Kooyong electorate.")
                
                # If not in Kooyong, suggest checking the address
                if not results['street_match']:
                    st.warning("🔍 Street not found in Kooyong database. This address may be outside the electorate.")
                else:
                    st.warning("⚠️ Street exists in Kooyong but geocoded location is outside the boundary. Try including a house number or suburb.")
            
            if results['street_match']:
                st.info(f"📍 Street segment matched: {results['matched_street_name']}")
                
                # Show all matching suburbs if multiple exist
                if len(results['matching_suburbs']) > 1:
                    st.warning("⚠️ Multiple suburbs found for this street:")
                    for match in results['matching_suburbs']:
                        st.write(f"   • {match['street_name']}, {match['suburb']}")
                    st.info("💡 For more precise results, include the suburb in your search")
                elif len(results['matching_suburbs']) == 1:
                    st.caption(f"Found in suburb: {results['matching_suburbs'][0]['suburb']}")
            else:
                st.warning("🔍 No street match found in the lookup database.")
                st.caption("This could mean the street is not in Kooyong, or there's a spelling variation.")
            
            # Display coordinates
            st.caption(f"Coordinates: {results['lat']:.6f}, {results['lon']:.6f}")
        
        with col2:
            st.subheader("🗺️ Map")
            
            # Create and display map
            map_obj = create_map(
                results['lat'], 
                results['lon'], 
                results['kooyong_gdf'], 
                results['address_input'],
                results['in_kooyong']
            )
            if map_obj:
                # Use session state to prevent map from clearing results
                st_folium(
                    map_obj, 
                    width=400, 
                    height=400,
                    key="kooyong_map"
                )

    # File status check
    with st.expander("📁 Data File Status"):
        if os.path.exists('kooyong_street_suburb_lookup.csv'):
            st.success("✅ Street lookup CSV found")
            if street_df is not None:
                st.caption(f"   → Contains {len(street_df)} street records")
        else:
            st.error("❌ kooyong_street_suburb_lookup.csv not found")
        
        if os.path.exists('E_VIC24_region.shp'):
            st.success("✅ Shapefile found")
        else:
            st.error("❌ E_VIC24_region.shp not found")

if __name__ == "__main__":
    main()
