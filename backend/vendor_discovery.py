"""
Vendor Discovery Service for PriceHunter
Uses Google Places API to find nearby local vendors
"""

import logging
import random
from typing import List, Optional, Dict, Tuple
from pydantic import BaseModel
import googlemaps
from googlemaps.exceptions import ApiError, Timeout, TransportError

logger = logging.getLogger(__name__)


class Vendor(BaseModel):
    """Discovered vendor information"""
    name: str
    phone: str
    address: str
    location: Dict[str, float]  # {"lat": float, "lng": float}
    place_id: Optional[str] = None
    business_type: Optional[str] = None
    rating: Optional[float] = None
    is_mock: bool = False


# Category to search query mapping
CATEGORY_SEARCH_QUERIES = {
    "groceries": [
        "grocery store near {location}",
        "vegetable vendors near {location}",
        "supermarket near {location}",
        "kirana store near {location}",
    ],
    "electronics": [
        "electronics shop near {location}",
        "mobile phone store near {location}",
        "computer store near {location}",
        "electronics showroom near {location}",
    ],
    "medicine": [
        "pharmacy near {location}",
        "medical store near {location}",
        "chemist near {location}",
    ],
    "clothing": [
        "clothing store near {location}",
        "garments shop near {location}",
        "fashion boutique near {location}",
    ],
    "hardware": [
        "hardware store near {location}",
        "tools shop near {location}",
        "building materials near {location}",
    ],
    "general": [
        "shops near {location}",
        "stores near {location}",
    ],
}


# Mock vendor data for fallback (realistic Indian businesses)
MOCK_VENDORS_BY_CITY = {
    "bengaluru": [
        {"name": "Sharma Electronics", "phone": "+919876543210", "address": "MG Road, Bengaluru"},
        {"name": "Raj Mobile Hub", "phone": "+919876543211", "address": "Commercial Street, Bengaluru"},
        {"name": "Krishna Traders", "phone": "+919876543212", "address": "SP Road, Bengaluru"},
        {"name": "Gupta & Sons", "phone": "+919876543213", "address": "Chickpet, Bengaluru"},
        {"name": "New Bharat Store", "phone": "+919876543214", "address": "Jayanagar, Bengaluru"},
        {"name": "Patel Electronics", "phone": "+919876543215", "address": "Koramangala, Bengaluru"},
        {"name": "Singh Mobile Center", "phone": "+919876543216", "address": "Indiranagar, Bengaluru"},
        {"name": "Reddy Super Market", "phone": "+919876543217", "address": "HSR Layout, Bengaluru"},
    ],
    "mumbai": [
        {"name": "Mehta Electronics", "phone": "+912234567890", "address": "Colaba, Mumbai"},
        {"name": "Shah Mobile Store", "phone": "+912234567891", "address": "Dadar, Mumbai"},
        {"name": "Kumar Trading Co", "phone": "+912234567892", "address": "Andheri, Mumbai"},
        {"name": "Joshi Stores", "phone": "+912234567893", "address": "Bandra, Mumbai"},
        {"name": "Desai Electronics", "phone": "+912234567894", "address": "Malad, Mumbai"},
        {"name": "Rao Super Market", "phone": "+912234567895", "address": "Powai, Mumbai"},
        {"name": "Agarwal Traders", "phone": "+912234567896", "address": "Borivali, Mumbai"},
    ],
    "delhi": [
        {"name": "Bansal Electronics", "phone": "+911123456789", "address": "Connaught Place, Delhi"},
        {"name": "Verma Mobile Hub", "phone": "+911123456788", "address": "Lajpat Nagar, Delhi"},
        {"name": "Kapoor Trading", "phone": "+911123456787", "address": "Saket, Delhi"},
        {"name": "Mittal Stores", "phone": "+911123456786", "address": "Karol Bagh, Delhi"},
        {"name": "Chopra Electronics", "phone": "+911123456785", "address": "Nehru Place, Delhi"},
        {"name": "Malhotra Super Market", "phone": "+911123456784", "address": "Rohini, Delhi"},
    ],
    "hyderabad": [
        {"name": "Reddy Electronics", "phone": "+914023456789", "address": "Ameerpet, Hyderabad"},
        {"name": "Naidu Mobile Center", "phone": "+914023456788", "address": "Kukatpally, Hyderabad"},
        {"name": "Chowdary Traders", "phone": "+914023456787", "address": "Dilsukhnagar, Hyderabad"},
        {"name": "Rao Super Bazaar", "phone": "+914023456786", "address": "Secunderabad, Hyderabad"},
        {"name": "Venkat Electronics", "phone": "+914023456785", "address": "Madhapur, Hyderabad"},
    ],
    "chennai": [
        {"name": "Raman Electronics", "phone": "+914423456789", "address": "T Nagar, Chennai"},
        {"name": "Krishna Mobile Store", "phone": "+914423456788", "address": "Anna Nagar, Chennai"},
        {"name": "Murugan Traders", "phone": "+914423456787", "address": "Velachery, Chennai"},
        {"name": "Suresh Super Market", "phone": "+914423456786", "address": "Adyar, Chennai"},
        {"name": "Velu Electronics", "phone": "+914423456785", "address": "Vadapalani, Chennai"},
    ],
    "default": [
        {"name": "Local Electronics Store", "phone": "+919800000001", "address": "Main Market"},
        {"name": "City Mobile Hub", "phone": "+919800000002", "address": "Commercial Street"},
        {"name": "New Traders", "phone": "+919800000003", "address": "Market Road"},
        {"name": "Super Bazaar", "phone": "+919800000004", "address": "Central Market"},
        {"name": "Grand Electronics", "phone": "+919800000005", "address": "Shopping Complex"},
    ],
}


def get_mock_vendors(location: str, count: int = 5) -> List[Vendor]:
    """
    Generate mock vendors for fallback
    Returns vendors with realistic Indian business names and phone numbers
    """
    location_lower = location.lower()
    
    # Try to match city from location string
    mock_data = MOCK_VENDORS_BY_CITY.get("default")
    for city, vendors in MOCK_VENDORS_BY_CITY.items():
        if city in location_lower:
            mock_data = vendors
            break
    
    # Add location to address if not already present
    vendors = []
    selected = random.sample(mock_data, min(count, len(mock_data)))
    
    for vendor_data in selected:
        # Generate random coordinates (mock)
        lat = 12.9716 + random.uniform(-0.5, 0.5)  # Bangalore-ish coordinates
        lng = 77.5946 + random.uniform(-0.5, 0.5)
        
        address = vendor_data["address"]
        if location not in address and location.lower() not in address.lower():
            address = f"{address}, {location}"
        
        vendors.append(Vendor(
            name=vendor_data["name"],
            phone=vendor_data["phone"],
            address=address,
            location={"lat": lat, "lng": lng},
            place_id=None,
            business_type="Mock",
            rating=round(random.uniform(3.5, 4.8), 1),
            is_mock=True
        ))
    
    logger.info(f"Generated {len(vendors)} mock vendors for {location}")
    return vendors


class VendorDiscoveryService:
    """Service for discovering nearby vendors using Google Places API"""
    
    def __init__(self, gmaps_client: Optional[googlemaps.Client] = None):
        self.gmaps = gmaps_client
        self.geocode_cache = {}  # Cache geocoding results
    
    def geocode_location(self, location: str) -> Optional[Tuple[float, float]]:
        """
        Geocode a location string to lat/lng coordinates
        Returns (lat, lng) tuple or None if geocoding fails
        """
        if not self.gmaps:
            logger.warning("Google Maps client not initialized, cannot geocode")
            return None
        
        # Check cache
        if location in self.geocode_cache:
            logger.debug(f"Using cached geocode for {location}")
            return self.geocode_cache[location]
        
        try:
            logger.info(f"Geocoding location: {location}")
            
            # Add "India" if not already present to improve accuracy
            search_location = location
            if "india" not in location.lower():
                search_location = f"{location}, India"
            
            geocode_result = self.gmaps.geocode(search_location)
            
            if not geocode_result:
                logger.warning(f"No geocoding results found for: {location}")
                return None
            
            # Extract lat/lng from first result
            geometry = geocode_result[0].get("geometry", {})
            location_data = geometry.get("location", {})
            
            lat = location_data.get("lat")
            lng = location_data.get("lng")
            
            if lat and lng:
                coords = (lat, lng)
                self.geocode_cache[location] = coords
                logger.info(f"Geocoded {location} to {coords}")
                return coords
            
            return None
            
        except (ApiError, Timeout, TransportError) as e:
            logger.error(f"Google Maps API error during geocoding: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during geocoding: {e}")
            return None
    
    def search_nearby_vendors(
        self,
        category: str,
        location: str,
        max_results: int = 10
    ) -> List[Vendor]:
        """
        Search for nearby vendors using Google Places API
        
        Args:
            category: Product category (groceries, electronics, etc.)
            location: Location string (e.g., "Koramangala Bangalore")
            max_results: Maximum number of vendors to return
        
        Returns:
            List of Vendor objects with phone numbers
        """
        if not self.gmaps:
            logger.warning("Google Maps client not available, using mock vendors")
            return get_mock_vendors(location, count=max_results)
        
        try:
            # Step 1: Geocode the location
            coords = self.geocode_location(location)
            
            if not coords:
                logger.warning(f"Could not geocode {location}, using mock vendors")
                return get_mock_vendors(location, count=max_results)
            
            lat, lng = coords
            
            # Step 2: Get search queries for this category
            search_queries = CATEGORY_SEARCH_QUERIES.get(
                category,
                CATEGORY_SEARCH_QUERIES["general"]
            )
            
            all_vendors = []
            seen_place_ids = set()
            
            # Step 3: Search using each query
            for query_template in search_queries:
                query = query_template.format(location=location)
                
                try:
                    logger.info(f"Searching Google Places: {query}")
                    
                    # Use places_nearby for better results
                    # Radius in meters (5km = 5000m)
                    places_result = self.gmaps.places(
                        query=query,
                        location=(lat, lng),
                        radius=5000,
                        language="en"
                    )
                    
                    results = places_result.get("results", [])
                    logger.info(f"Found {len(results)} results for query: {query}")
                    
                    # Step 4: Fetch place details for each result
                    for place in results[:5]:  # Limit to 5 per query to avoid rate limits
                        place_id = place.get("place_id")
                        
                        if place_id in seen_place_ids:
                            continue
                        
                        seen_place_ids.add(place_id)
                        
                        # Fetch detailed information including phone number
                        try:
                            place_details = self.gmaps.place(
                                place_id,
                                fields=[
                                    "name",
                                    "formatted_phone_number",
                                    "international_phone_number",
                                    "formatted_address",
                                    "geometry",
                                    "rating"
                                ]
                            )
                            
                            result = place_details.get("result", {})
                            
                            # Extract phone number (prioritize international format)
                            phone = (
                                result.get("international_phone_number") or
                                result.get("formatted_phone_number")
                            )
                            
                            # Step 5: Filter out results without phone numbers
                            if not phone:
                                logger.debug(
                                    f"Skipping {result.get('name')} - no phone number"
                                )
                                continue
                            
                            # Extract location coordinates
                            geometry = result.get("geometry", {})
                            location_data = geometry.get("location", {})
                            
                            vendor = Vendor(
                                name=result.get("name", "Unknown"),
                                phone=phone,
                                address=result.get("formatted_address", ""),
                                location={
                                    "lat": location_data.get("lat", lat),
                                    "lng": location_data.get("lng", lng)
                                },
                                place_id=place_id,
                                business_type="Local Business",
                                rating=result.get("rating"),
                                is_mock=False
                            )
                            
                            all_vendors.append(vendor)
                            logger.debug(f"Added vendor: {vendor.name} ({vendor.phone})")
                            
                        except Exception as e:
                            logger.warning(
                                f"Error fetching place details for {place_id}: {e}"
                            )
                            continue
                
                except (ApiError, Timeout, TransportError) as e:
                    logger.error(f"Google Places API error for query '{query}': {e}")
                    continue
                except Exception as e:
                    logger.error(f"Unexpected error searching places: {e}")
                    continue
            
            # Step 6: Return top N vendors
            if not all_vendors:
                logger.warning("No vendors found with phone numbers, using mock data")
                return get_mock_vendors(location, count=max_results)
            
            # Sort by rating (if available) and return top results
            all_vendors.sort(
                key=lambda v: (v.rating or 0, v.name),
                reverse=True
            )
            
            top_vendors = all_vendors[:max_results]
            logger.info(
                f"Discovered {len(top_vendors)} vendors with phone numbers "
                f"near {location}"
            )
            
            return top_vendors
            
        except Exception as e:
            logger.error(f"Critical error in vendor discovery: {e}")
            return get_mock_vendors(location, count=max_results)


def discover_vendors(
    category: str,
    location: str,
    gmaps_client: Optional[googlemaps.Client] = None,
    max_results: int = 10
) -> List[Vendor]:
    """
    Convenience function for vendor discovery
    
    Args:
        category: Product category
        location: Location string
        gmaps_client: Optional Google Maps client
        max_results: Maximum vendors to return
    
    Returns:
        List of discovered vendors
    """
    service = VendorDiscoveryService(gmaps_client)
    return service.search_nearby_vendors(category, location, max_results)
