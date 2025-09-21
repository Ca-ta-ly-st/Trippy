"""
Standalone Flight Search Function using SerpAPI.

This module provides a standalone function to search for flights using SerpAPI Google Flights.
It can be used independently without any server infrastructure.
"""

import os
from typing import Dict, Any, List, Optional
from serpapi import GoogleSearch
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def search_flights(
    origin: str, 
    destination: str, 
    outbound_date: str, 
    return_date: Optional[str] = None
) -> List[Dict[str, str]]:
    """
    Search for flights using SerpAPI Google Flights.
    
    Args:
        origin: Departure airport code (e.g., 'ATL', 'JFK')
        destination: Arrival airport code (e.g., 'LAX', 'ORD') 
        outbound_date: Departure date in YYYY-MM-DD format
        return_date: Return date for round trips in YYYY-MM-DD format (optional)
        
    Returns:
        List of flight dictionaries containing:
        - airline: Airline name
        - price: Flight price
        - duration: Total flight duration
        - stops: Number of stops
        - departure: Departure airport and time
        - arrival: Arrival airport and time
        - travel_class: Travel class
        - airline_logo: Airline logo URL (if available)
        
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
        "engine": "google_flights",
        "hl": "en",
        "gl": "us",
        "departure_id": origin.strip().upper(),
        "arrival_id": destination.strip().upper(),
        "outbound_date": outbound_date,
        "currency": "USD",
        "type": "2"  # One-way by default
    }
    
    # Configure for round trip if return date provided
    if return_date:
        search_params["return_date"] = return_date
        search_params["type"] = "1"  # Round trip
    
    try:
        print(f"Searching flights: {origin} → {destination}")
        print(f"Outbound: {outbound_date}" + (f", Return: {return_date}" if return_date else ""))
        
        # Execute search
        search = GoogleSearch(search_params)
        results = search.get_dict()
        
        # Check for API errors
        if "error" in results:
            raise Exception(f"SerpAPI error: {results['error']}")
        
        # Process and return formatted results
        return _format_flight_data(results)
        
    except Exception as e:
        print(f"Flight search failed: {str(e)}")
        raise


def _format_flight_data(raw_results: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Format raw SerpAPI results into standardized flight data.
    
    Args:
        raw_results: Raw search results from SerpAPI
        
    Returns:
        List of formatted flight dictionaries
    """
    best_flights = raw_results.get("best_flights", [])
    
    if not best_flights:
        print("No flights found in search results")
        return []
    
    print(f"Processing {len(best_flights)} flights...")
    
    formatted_flights = []
    
    for flight in best_flights:
        # Skip flights without flight segments
        if not flight.get("flights") or len(flight["flights"]) == 0:
            continue
        
        # Get primary flight segment (first leg)
        primary_segment = flight["flights"][0]
        
        # Extract departure information
        departure_info = _extract_airport_info(
            primary_segment.get("departure_airport", {}), 
            "departure"
        )
        
        # Extract arrival information  
        arrival_info = _extract_airport_info(
            primary_segment.get("arrival_airport", {}),
            "arrival"
        )
        
        # Format flight duration
        total_duration = flight.get("total_duration", 0)
        duration_str = f"{total_duration} min" if total_duration else "N/A"
        
        # Determine stops
        num_segments = len(flight["flights"])
        stops = "Nonstop" if num_segments == 1 else f"{num_segments - 1} stop(s)"
        
        # Build flight record
        flight_record = {
            "airline": primary_segment.get("airline", "Unknown Airline"),
            "price": str(flight.get("price", "N/A")),
            "duration": duration_str,
            "stops": stops,
            "departure": departure_info,
            "arrival": arrival_info,
            "travel_class": primary_segment.get("travel_class", "Economy"),
            "airline_logo": primary_segment.get("airline_logo", "")
        }
        
        formatted_flights.append(flight_record)
    
    return formatted_flights


def _extract_airport_info(airport_data: Dict[str, Any], info_type: str) -> str:
    """
    Extract and format airport information from API response.
    
    Args:
        airport_data: Airport data dictionary from API
        info_type: Either 'departure' or 'arrival'
        
    Returns:
        Formatted airport information string
    """
    if not isinstance(airport_data, dict):
        return f"Unknown {info_type}"
    
    airport_name = airport_data.get("name", "Unknown Airport")
    airport_code = airport_data.get("id", "???")
    flight_time = airport_data.get("time", "N/A")
    
    return f"{airport_name} ({airport_code}) at {flight_time}"


def display_flights(flights: List[Dict[str, str]], limit: Optional[int] = None) -> None:
    """
    Display flight results in a formatted table.
    
    Args:
        flights: List of flight dictionaries
        limit: Maximum number of flights to display (optional)
    """
    if not flights:
        return ["No flights found."]

    display_count = len(flights) if limit is None else min(limit, len(flights))
    result = []
    result.append(f"\n{'='*80}")
    result.append(f"FLIGHT SEARCH RESULTS (Showing {display_count} of {len(flights)} flights)")
    result.append(f"{'='*80}")

    for i, flight in enumerate(flights[:display_count], 1):
        flight_str = [
            f"\n✈️  Flight Option {i}:",
            f"   🏢 Airline: {flight['airline']}",
            f"   💰 Price: {flight['price']}$",
            f"   ⏱️  Duration: {flight['duration']}",
            f"   🛑 Stops: {flight['stops']}",
            f"   🛫 Departure: {flight['departure']}",
            f"   🛬 Arrival: {flight['arrival']}",
            f"   🎫 Class: {flight['travel_class']}"
        ]
        result.extend(flight_str)
    return result


def get_cheapest_flight(flights: List[Dict[str, str]]) -> Optional[Dict[str, str]]:
    """
    Find the cheapest flight from search results.
    
    Args:
        flights: List of flight dictionaries
        
    Returns:
        Cheapest flight dictionary or None if no flights
    """
    if not flights:
        return None
    
    # Filter out flights with non-numeric prices
    valid_flights = []
    for flight in flights:
        try:
            price_str = flight['price'].replace('$', '').replace(',', '')
            float(price_str)  # Test if convertible to number
            valid_flights.append(flight)
        except (ValueError, AttributeError):
            continue
    
    if not valid_flights:
        return None
    
    # Find flight with minimum price
    return min(valid_flights, key=lambda f: float(f['price'].replace('$', '').replace(',', '')))


# Example usage and testing
if __name__ == "__main__":
    """
    Example usage of the flight search function.
    """
    
    # Example 1: One-way flight
    print("Example 1: One-way flight search")
    try:
        flights = search_flights(
            origin="NYC",
            destination="LAX", 
            outbound_date="2025-07-15"
        )
        
        display_flights(flights, limit=3)
        
        # Find cheapest option
        cheapest = get_cheapest_flight(flights)
        if cheapest:
            print(f"\n🏆 Cheapest Option: {cheapest['airline']} - {cheapest['price']}")
            
    except Exception as e:
        print(f"Example 1 failed: {e}")
    
    print("\n" + "="*80)
    
    # Example 2: Round-trip flight
    print("Example 2: Round-trip flight search")
    try:
        flights = search_flights(
            origin="ATL",
            destination="MIA",
            outbound_date="2025-08-10",
            return_date="2025-08-17"
        )
        
        display_flights(flights, limit=2)
        
    except Exception as e:
        print(f"Example 2 failed: {e}")
        print("\nSetup instructions:")
        print("1. Install dependencies: pip install serpapi python-dotenv")
        print("2. Get API key from https://serpapi.com/")
        print("3. Create .env file with: SERP_API_KEY=your_api_key_here")