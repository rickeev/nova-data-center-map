import json
import time
import re
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

# --- Street suffix replacements ---
suffix_map = {
    "Street": "St",
    "Avenue": "Ave",
    "Boulevard": "Blvd",
    "Drive": "Dr",
    "Court": "Ct",
    "Circle": "Cir",
    "Place": "Pl",
    "Plaza": "Plz",
    "Lane": "Ln",
    "Road": "Rd",
    "Terrace": "Ter",
    "Parkway": "Pkwy",
    "Highway": "Hwy",
    "Way": "Way"
}

def abbreviate_suffix(address):
    """Replace common street suffixes with USPS abbreviations."""
    for full, abbr in suffix_map.items():
        address = re.sub(rf"\b{full}\b", abbr, address, flags=re.IGNORECASE)
    return address

def clean_address(address):
    """Clean address to improve geocoding success rate"""
    # Remove building identifiers in parentheses
    address = re.sub(r'\s*\([^)]*\)', '', address)
    
    # Handle address ranges - take just the first number
    address = re.sub(r'(\d+)-\d+', r'\1', address)
    
    # Make sure there's a space after commas
    address = re.sub(r',(?!\s)', ', ', address)
    
    # Abbreviate street suffixes
    address = abbreviate_suffix(address)
    
    return address

def try_geocode(geolocator, address, max_retries=3, delay=1.5):
    """Try to geocode with retries for timeouts"""
    for attempt in range(max_retries):
        try:
            return geolocator.geocode(address, exactly_one=True)
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            if attempt == max_retries - 1:
                print(f"⚠️ Geocoding error after {max_retries} attempts for {address}: {e}")
                return None
            time.sleep(delay)  # Wait before retrying

def try_alternative_formats(geolocator, original_address, city, state, zip_code):
    """Try different address formats if initial geocoding fails"""
    formats = []
    clean_addr = clean_address(original_address)
    
    # Format 1: Standard clean format
    formats.append(f"{clean_addr}, {city}, {state} {zip_code}")
    
    # Format 2: Without street suffix for numbered streets
    if re.search(r'\d+\s+(St|Street|Dr|Drive|Rd|Road|Ln|Lane|Ave|Avenue|Blvd|Boulevard|Plz|Plaza|Pkwy|Parkway|Cir|Circle|Ct|Court)', clean_addr, re.IGNORECASE):
        simple_addr = re.sub(r'(\d+)\s+(St|Street|Dr|Drive|Rd|Road|Ln|Lane|Ave|Avenue|Blvd|Boulevard|Plz|Plaza|Pkwy|Parkway|Cir|Circle|Ct|Court)(\b|$)', r'\1', clean_addr, flags=re.IGNORECASE)
        formats.append(f"{simple_addr}, {city}, {state} {zip_code}")
    
    # Format 3: Without city name (new format)
    formats.append(f"{clean_addr}, {state} {zip_code}")
    
    # Try each format
    for addr_format in formats:
        location = try_geocode(geolocator, addr_format)
        if location:
            print(f"✓ Successfully geocoded using format: {addr_format}")
            return location
    
    return None

def geocode_intersection(geolocator, street1, street2, city, state, zip_code):
    """
    Geocode an intersection by finding where two streets intersect
    """
    try:
        # Import shapely
        from shapely.geometry import shape, LineString, Point
    except ImportError:
        print("❌ Shapely is required for intersection geocoding. Please install with: pip install shapely")
        return None
    
    # Step 1: Query first street - try with and without city
    street1_query = f"{street1}, {city}, {state} {zip_code}"
    print(f"Geocoding first street: {street1_query}")
    street1_location = try_geocode(geolocator, street1_query)
    
    # Try without city if first attempt failed
    if not street1_location:
        street1_query_no_city = f"{street1}, {state} {zip_code}"
        print(f"Retrying first street without city: {street1_query_no_city}")
        street1_location = try_geocode(geolocator, street1_query_no_city)
    
    if not street1_location:
        print(f"❌ Could not find first street: {street1}")
        return None
    
    # Step 2: Query second street - try with and without city
    street2_query = f"{street2}, {city}, {state} {zip_code}"
    print(f"Geocoding second street: {street2_query}")
    street2_location = try_geocode(geolocator, street2_query)
    
    # Try without city if first attempt failed
    if not street2_location:
        street2_query_no_city = f"{street2}, {state} {zip_code}"
        print(f"Retrying second street without city: {street2_query_no_city}")
        street2_location = try_geocode(geolocator, street2_query_no_city)
    
    if not street2_location:
        print(f"❌ Could not find second street: {street2}")
        return None
    
    # Step 3: Create a simple intersection point from the two coordinates
    # This is a fallback approach since we can't get the full geometry
    street1_point = Point(street1_location.longitude, street1_location.latitude)
    street2_point = Point(street2_location.longitude, street2_location.latitude)
    
    # Calculate midpoint as a simple approximation of the intersection
    intersection_point = Point(
        (street1_point.x + street2_point.x) / 2,
        (street1_point.y + street2_point.y) / 2
    )
    
    print(f"⚠️ Using simple midpoint approximation for intersection")
    
    # Create a location object with the intersection coordinates
    return {
        'address': f"Intersection of {street1} and {street2}, {city}, {state} {zip_code}",
        'latitude': intersection_point.y,
        'longitude': intersection_point.x
    }

def parse_data_centers_with_geocoding(file_path):
    geolocator = Nominatim(user_agent="nova_geojson_generator_v2")
    features = []
    failed = []
    failed_with_names = []  # Store both name and address for failed geocodes
    retry_failed = True

    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    for i in range(0, len(lines), 4):
        if i + 3 >= len(lines):
            break
            
        # Preserve the exact name from the file
        name = lines[i].strip()
        company = lines[i + 1].strip()
        street = lines[i + 2].strip()
        last_line = lines[i + 3].strip()

        parts = last_line.split()
        zip_code = parts[0]
        city_and_company = ' '.join(parts[1:])

        # Remove company name from end of city line
        city = city_and_company.replace(company, '').strip()
        state = "VA"

        # Clean street name for geocoding and create full address
        clean_street = abbreviate_suffix(street)
        full_address = f"{clean_street}, {city}, {state} {zip_code}"

        # Handle intersection addresses
        if '/' in street:
            print(f"Processing intersection: {street}")
            streets = [s.strip() for s in street.split('/')]
            if len(streets) == 2:
                intersection_result = geocode_intersection(geolocator, streets[0], streets[1], city, state, zip_code)
                if intersection_result:
                    coordinates = [intersection_result['longitude'], intersection_result['latitude']]
                    print(f"✅ Found intersection coordinates: {coordinates}")
                    
                    feature = {
                        "type": "Feature",
                        "properties": {
                            "name": name,  # Preserve the original name
                            "company": company,
                            "street": street,  # Original street name
                            "city": city,
                            "zip": zip_code,
                            "address": full_address,
                            "geocoded_address": intersection_result['address']
                        },
                        "geometry": {
                            "type": "Point",
                            "coordinates": coordinates
                        }
                    }
                    
                    features.append(feature)
                else:
                    failed.append(full_address)
                    failed_with_names.append((name, full_address))  # Store both name and address
                    print(f"❌ Failed to geocode intersection: {full_address}")
                    
                    feature = {
                        "type": "Feature",
                        "properties": {
                            "name": name,  # Preserve the original name
                            "company": company,
                            "street": street,
                            "city": city,
                            "zip": zip_code,
                            "address": full_address,
                            "geocoded_address": ""
                        },
                        "geometry": {
                            "type": "Point",
                            "coordinates": []
                        }
                    }
                    
                    features.append(feature)
                
                # Continue to next address
                time.sleep(1.2)  # Respect Nominatim usage policy with a slight delay
                continue
        
        # Regular address geocoding
        try:
            print(f"Geocoding: {full_address}")
            location = try_geocode(geolocator, full_address)
            
            # If initial geocoding fails, try alternative formats
            if not location:
                print(f"⚠️ Initial geocoding failed for {full_address}, trying alternative formats...")
                location = try_alternative_formats(geolocator, street, city, state, zip_code)
            
            if location:
                coordinates = [location.longitude, location.latitude]
                geocoded_address = location.address
                print(f"✅ Successfully geocoded: {geocoded_address}")
            else:
                coordinates = []
                geocoded_address = ""
                failed.append(full_address)
                failed_with_names.append((name, full_address))  # Store both name and address
                print(f"❌ Address not found: {full_address}")
        except Exception as e:
            coordinates = []
            geocoded_address = ""
            failed.append(full_address)
            failed_with_names.append((name, full_address))  # Store both name and address
            print(f"❌ Error geocoding {full_address}: {e}")

        time.sleep(1.2)  # Respect Nominatim usage policy with a slight delay

        feature = {
            "type": "Feature",
            "properties": {
                "name": name,  # Preserve the original name
                "company": company,
                "street": street,  # Original street name
                "city": city,
                "zip": zip_code,
                "address": full_address,
                "geocoded_address": geocoded_address
            },
            "geometry": {
                "type": "Point",
                "coordinates": coordinates
            }
        }

        features.append(feature)

    # Save results
    geojson_data = {
        "type": "FeatureCollection",
        "features": features
    }

    with open("nova_data_centers_improved.geojson", "w", encoding='utf-8') as out_file:
        json.dump(geojson_data, out_file, indent=2)

    print("\n✅ GeoJSON file created: nova_data_centers_improved.geojson")

    if failed:
        with open("failed_geocodes.txt", "w", encoding='utf-8') as fail_file:
            for name, addr in failed_with_names:
                fail_file.write(f"{name} | {addr}\n")
        print(f"⚠️ {len(failed)} addresses failed to geocode. See failed_geocodes.txt.")
        
        # Optionally retry failed addresses with different parameters
        if retry_failed:
            retry_count = 0
            still_failed = []
            still_failed_with_names = []  # Store both name and address for still failed geocodes
            print("\nRetrying failed addresses with relaxed parameters...")
            for idx, address in enumerate(failed):
                name = failed_with_names[idx][0]  # Get the name from the corresponding tuple
                
                # Extract basic components from address
                match = re.match(r'(.*), ([^,]+), VA (\d+)', address)
                if match:
                    street, city, zip_code = match.groups()
                    
                    # Skip intersection addresses in this retry phase
                    if '/' in street:
                        still_failed.append(address)
                        still_failed_with_names.append((name, address))
                        continue
                    
                    # Try with just the numeric part of the address and city
                    numeric_part = re.search(r'(\d+)', street)
                    if numeric_part:
                        # Add more context to avoid city-level matches
                        street_type = re.search(r'\b(St|Street|Dr|Drive|Rd|Road|Ln|Lane|Ave|Avenue|Blvd|Boulevard|Plz|Plaza|Pkwy|Parkway|Cir|Circle|Ct|Court)\b', street, re.IGNORECASE)
                        street_type_text = street_type.group(1) if street_type else ""
                        
                        # Try with and without city name
                        formats = [
                            f"{numeric_part.group(1)} {street_type_text}, {city}, VA {zip_code}",
                            f"{numeric_part.group(1)} {street_type_text}, VA {zip_code}"
                        ]
                        
                        location = None
                        for simplified in formats:
                            print(f"Trying simplified: {simplified}")
                            location = try_geocode(geolocator, simplified)
                            
                            if location:
                                # Verify it's not just a city match
                                address_parts = location.address.lower().split(city.lower() if city.lower() in location.address.lower() else zip_code)
                                if len(address_parts) > 1 and address_parts[0].strip():
                                    retry_count += 1
                                    print(f"✓ Success with simplified address: {simplified}")
                                    
                                    # Update the corresponding feature
                                    for feature in features:
                                        if feature["properties"]["address"] == address:
                                            feature["geometry"]["coordinates"] = [location.longitude, location.latitude]
                                            feature["properties"]["geocoded_address"] = location.address
                                            break
                                    
                                    break  # Break out of the formats loop
                            
                            time.sleep(1.2)  # Respect Nominatim usage policy with a slight delay
                        
                        # If any format succeeded, continue to next address
                        if location:
                            continue
                
                still_failed.append(address)
                still_failed_with_names.append((name, address))
                time.sleep(1.2)
            
            print(f"Recovered {retry_count} of {len(failed)} failed addresses")
            if still_failed:
                with open("still_failed_geocodes.txt", "w", encoding='utf-8') as still_fail_file:
                    for name, addr in still_failed_with_names:
                        still_fail_file.write(f"{name} | {addr}\n")
    
    # Update the output file with any recovered addresses
    if retry_failed and "retry_count" in locals() and retry_count > 0:
        with open("nova_data_centers_improved.geojson", "w", encoding='utf-8') as out_file:
            json.dump(geojson_data, out_file, indent=2)
        print(f"✅ Updated GeoJSON file with {retry_count} recovered addresses")

# Run the function
parse_data_centers_with_geocoding("nova_data_centers.txt")