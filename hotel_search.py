"""
Standalone Hotel Search Function using SerpAPI.

This module provides a standalone function to search for hotels using SerpAPI Google Hotels.
It can be used independently without any server infrastructure.
"""

import os
from typing import Dict, Any, List, Optional
from serpapi import GoogleSearch
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def search_hotels(
    location: str,
    check_in_date: str,
    check_out_date: str,
    adults: int = 2,
    children: int = 0,
    children_ages: Optional[str] = None,
    sort_by: Optional[int] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    hotel_class: Optional[str] = None,
    rating: Optional[int] = None,
    vacation_rentals: bool = False
) -> List[Dict[str, Any]]:
    """
    Search for hotels using SerpAPI Google Hotels.
    
    Args:
        location: Search location (e.g., 'New York', 'Paris', 'Bali Resorts')
        check_in_date: Check-in date in YYYY-MM-DD format
        check_out_date: Check-out date in YYYY-MM-DD format
        adults: Number of adults (default: 2)
        children: Number of children (default: 0)
        children_ages: Ages of children, comma-separated (e.g., '5,8,10')
        sort_by: Sort order (3=Lowest price, 8=Highest rating, 13=Most reviewed)
        min_price: Minimum price per night
        max_price: Maximum price per night
        hotel_class: Hotel class filter, comma-separated (e.g., '3,4,5')
        rating: Minimum rating filter (7=3.5+, 8=4.0+, 9=4.5+)
        vacation_rentals: Search vacation rentals instead of hotels
        
    Returns:
        List of hotel dictionaries containing:
        - name: Hotel name
        - type: Property type (hotel/vacation rental)
        - price_per_night: Lowest rate per night
        - total_price: Total price for stay
        - rating: Overall rating
        - reviews: Number of reviews
        - hotel_class: Hotel class/stars
        - location: GPS coordinates
        - amenities: List of amenities
        - images: List of image URLs
        - check_in_time: Check-in time
        - check_out_time: Check-out time
        - property_token: Token for detailed property info
        
    Raises:
        ValueError: If SERP_API_KEY is not found in environment variables
        Exception: If SerpAPI request fails
    """
    # Validate API key
    api_key = os.getenv("SERP_API_KEY")
    if not api_key:
        raise ValueError(
            "SERP_API_KEY not found in environment variables. "
            "Please set it in your .env file or environment."
        )
    
    # Prepare search parameters
    search_params = {
        "api_key": api_key,
        "engine": "google_hotels",
        "q": location.strip(),
        "check_in_date": check_in_date,
        "check_out_date": check_out_date,
        "adults": adults,
        "children": children,
        "currency": "USD",
        "gl": "us",
        "hl": "en"
    }
    
    # Add optional parameters
    if children_ages:
        search_params["children_ages"] = children_ages
    
    if sort_by:
        search_params["sort_by"] = sort_by
        
    if min_price:
        search_params["min_price"] = min_price
        
    if max_price:
        search_params["max_price"] = max_price
        
    if hotel_class:
        search_params["hotel_class"] = hotel_class
        
    if rating:
        search_params["rating"] = rating
        
    if vacation_rentals:
        search_params["vacation_rentals"] = True
    
    try:
        print(f"Searching hotels in: {location}")
        print(f"Check-in: {check_in_date}, Check-out: {check_out_date}")
        print(f"Guests: {adults} adults" + (f", {children} children" if children > 0 else ""))
        
        # Execute search
        search = GoogleSearch(search_params)
        results = search.get_dict()
        
        # Check for API errors
        if "error" in results:
            raise Exception(f"SerpAPI error: {results['error']}")
        
        # Process and return formatted results
        return _format_hotel_data(results)
        
    except Exception as e:
        print(f"Hotel search failed: {str(e)}")
        raise


def _format_hotel_data(raw_results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Format raw SerpAPI results into standardized hotel data.
    
    Args:
        raw_results: Raw search results from SerpAPI
        
    Returns:
        List of formatted hotel dictionaries
    """
    properties = raw_results.get("properties", [])
    ads = raw_results.get("ads", [])
    
    # Combine properties and ads for more comprehensive results
    all_hotels = properties + ads
    
    if not all_hotels:
        print("No hotels found in search results")
        return []
    
    print(f"Processing {len(all_hotels)} hotels ({len(properties)} properties + {len(ads)} ads)...")
    
    formatted_hotels = []
    
    for hotel in all_hotels:
        # Skip hotels without basic information
        if not hotel.get("name"):
            continue
        
        # Extract pricing information
        price_info = _extract_price_info(hotel)
        
        # Extract location information
        gps_coords = hotel.get("gps_coordinates", {})
        location_str = f"Lat: {gps_coords.get('latitude', 'N/A')}, Lon: {gps_coords.get('longitude', 'N/A')}"
        
        # Extract amenities
        amenities = hotel.get("amenities", [])
        if isinstance(amenities, list):
            amenities_str = ", ".join(amenities[:5])  # Limit to first 5 amenities
            if len(amenities) > 5:
                amenities_str += f" (and {len(amenities) - 5} more)"
        else:
            amenities_str = "N/A"
        
        # Extract images
        images = hotel.get("images", [])
        image_urls = []
        if images:
            for img in images[:3]:  # Get first 3 images
                if isinstance(img, dict):
                    image_urls.append(img.get("original_image", img.get("thumbnail", "")))
        
        # Build hotel record
        hotel_record = {
            "name": hotel.get("name", "Unknown Hotel"),
            "type": hotel.get("type", "hotel"),
            "price_per_night": price_info["per_night"],
            "total_price": price_info["total"],
            "rating": hotel.get("overall_rating", "N/A"),
            "reviews": hotel.get("reviews", 0),
            "hotel_class": _format_hotel_class(hotel),
            "location": location_str,
            "amenities": amenities_str,
            "images": image_urls,
            "check_in_time": hotel.get("check_in_time", "N/A"),
            "check_out_time": hotel.get("check_out_time", "N/A"),
            "property_token": hotel.get("property_token", ""),
            "link": hotel.get("link", ""),
            "description": hotel.get("description", "")[:200] + "..." if hotel.get("description", "") else "N/A"
        }
        
        formatted_hotels.append(hotel_record)
    
    return formatted_hotels


def _extract_price_info(hotel_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract and format price information from hotel data.
    
    Args:
        hotel_data: Hotel data dictionary from API
        
    Returns:
        Dictionary with formatted price information
    """
    # Try different price fields
    rate_per_night = hotel_data.get("rate_per_night", {})
    total_rate = hotel_data.get("total_rate", {})
    
    # For ads, price might be directly available
    ad_price = hotel_data.get("price", "")
    
    if rate_per_night and isinstance(rate_per_night, dict):
        per_night = rate_per_night.get("lowest", "N/A")
    elif ad_price:
        per_night = ad_price
    else:
        per_night = "N/A"
    
    if total_rate and isinstance(total_rate, dict):
        total = total_rate.get("lowest", "N/A")
    else:
        total = "N/A"
    
    return {
        "per_night": per_night,
        "total": total
    }


def _format_hotel_class(hotel_data: Dict[str, Any]) -> str:
    """
    Extract and format hotel class information.
    
    Args:
        hotel_data: Hotel data dictionary from API
        
    Returns:
        Formatted hotel class string
    """
    # Try different class fields
    hotel_class = hotel_data.get("hotel_class")
    extracted_class = hotel_data.get("extracted_hotel_class")
    
    if extracted_class:
        return f"{extracted_class}-star"
    elif hotel_class:
        if isinstance(hotel_class, str):
            return hotel_class
        elif isinstance(hotel_class, int):
            return f"{hotel_class}-star"
    
    return "N/A"


def display_hotels(hotels: List[Dict[str, Any]], limit: Optional[int] = None) -> None:
    """
    Display hotel results in a formatted table.
    
    Args:
        hotels: List of hotel dictionaries
        limit: Maximum number of hotels to display (optional)
    """
    if not hotels:
        print("No hotels found.")
        return
    
    display_count = len(hotels) if limit is None else min(limit, len(hotels))
    
    print(f"\n{'='*80}")
    print(f"HOTEL SEARCH RESULTS (Showing {display_count} of {len(hotels)} hotels)")
    print(f"{'='*80}")
    
    for i, hotel in enumerate(hotels[:display_count], 1):
        print(f"\n🏨 Hotel Option {i}:")
        print(f"   🏢 Name: {hotel['name']}")
        print(f"   🏷️  Type: {hotel['type']}")
        print(f"   💰 Price per night: {hotel['price_per_night']}")
        print(f"   💵 Total price: {hotel['total_price']}")
        print(f"   ⭐ Rating: {hotel['rating']} ({hotel['reviews']} reviews)")
        print(f"   🌟 Class: {hotel['hotel_class']}")
        print(f"   📍 Location: {hotel['location']}")
        print(f"   🏨 Amenities: {hotel['amenities']}")
        print(f"   ⏰ Check-in: {hotel['check_in_time']} | Check-out: {hotel['check_out_time']}")
        
        if hotel['description'] and hotel['description'] != "N/A":
            print(f"   📝 Description: {hotel['description']}")
        
        if hotel['images']:
            print(f"   🖼️  Images: {len(hotel['images'])} available")
        
        if hotel['link']:
            print(f"   🔗 Link: {hotel['link']}")


def get_cheapest_hotel(hotels: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Find the cheapest hotel from search results.
    
    Args:
        hotels: List of hotel dictionaries
        
    Returns:
        Cheapest hotel dictionary or None if no hotels
    """
    if not hotels:
        return None
    
    # Filter out hotels with non-numeric prices
    valid_hotels = []
    for hotel in hotels:
        try:
            price_str = hotel['price_per_night'].replace('$', '').replace(',', '')
            float(price_str)  # Test if convertible to number
            valid_hotels.append(hotel)
        except (ValueError, AttributeError):
            continue
    
    if not valid_hotels:
        return None
    
    # Find hotel with minimum price
    return min(valid_hotels, key=lambda h: float(h['price_per_night'].replace('$', '').replace(',', '')))


def get_highest_rated_hotel(hotels: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Find the highest rated hotel from search results.
    
    Args:
        hotels: List of hotel dictionaries
        
    Returns:
        Highest rated hotel dictionary or None if no hotels
    """
    if not hotels:
        return None
    
    # Filter out hotels with non-numeric ratings
    valid_hotels = []
    for hotel in hotels:
        try:
            rating = hotel['rating']
            if rating != "N/A":
                float(rating)  # Test if convertible to number
                valid_hotels.append(hotel)
        except (ValueError, TypeError):
            continue
    
    if not valid_hotels:
        return None
    
    # Find hotel with maximum rating
    return max(valid_hotels, key=lambda h: float(h['rating']))


# Example usage and testing
if __name__ == "__main__":
    """
    Example usage of the hotel search function.
    """
    
    # Example 1: Basic hotel search
    print("Example 1: Basic hotel search in New York")
    try:
        hotels = search_hotels(
            location="New York",
            check_in_date="2025-07-15",
            check_out_date="2025-07-18",
            adults=2
        )
        
        display_hotels(hotels, limit=3)
        
        # Find cheapest option
        cheapest = get_cheapest_hotel(hotels)
        if cheapest:
            print(f"\n💰 Cheapest Option: {cheapest['name']} - {cheapest['price_per_night']} per night")
        
        # Find highest rated option
        highest_rated = get_highest_rated_hotel(hotels)
        if highest_rated:
            print(f"⭐ Highest Rated: {highest_rated['name']} - {highest_rated['rating']} stars")
            
    except Exception as e:
        print(f"Example 1 failed: {e}")
    
    print("\n" + "="*80)
    
    # Example 2: Vacation rentals search with filters
    print("Example 2: Vacation rentals search in Bali with filters")
    try:
        hotels = search_hotels(
            location="Bali",
            check_in_date="2025-08-10",
            check_out_date="2025-08-17",
            adults=4,
            children=2,
            children_ages="8,12",
            vacation_rentals=True,
            sort_by=8,  # Sort by highest rating
            rating=8    # 4.0+ rating filter
        )
        
        display_hotels(hotels, limit=2)
        
    except Exception as e:
        print(f"Example 2 failed: {e}")
    
    print("\n" + "="*80)
    
    # Example 3: Luxury hotel search
    print("Example 3: Luxury hotel search in Paris")
    try:
        hotels = search_hotels(
            location="Paris luxury hotels",
            check_in_date="2025-09-01",
            check_out_date="2025-09-05",
            adults=2,
            hotel_class="4,5",  # 4-star and 5-star only
            sort_by=8,          # Sort by highest rating
            min_price=200       # Minimum $200 per night
        )
        
        display_hotels(hotels, limit=2)
        
    except Exception as e:
        print(f"Example 3 failed: {e}")
        print("\nSetup instructions:")
        print("1. Install dependencies: pip install serpapi python-dotenv")
        print("2. Get API key from https://serpapi.com/")
        print("3. Create .env file with: SERP_API_KEY=your_api_key_here")