import os
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime
import json
from llm import LLM
llm = LLM(os.getenv("api_base"), os.getenv("deployment_name"), os.getenv("api_version"))
def get_llm_suggestions(budget: float, start_date: str, end_date: str):
    """
    Get destination suggestions from OpenAI's GPT based on budget and dates.
    Returns only destination names and countries.
    """
    # Calculate trip duration
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    duration = (end - start).days + 1

    # Construct the prompt
    prompt = f"""Given the following travel parameters:
    - Total Budget: ₹{budget}
    - Start Date: {start_date}
    - End Date: {end_date}
    - Duration: {duration} days

    Suggest 5 suitable travel destinations that fit within this budget.
    For each destination, provide only the city name and country.

    Return the response in this exact JSON format:
    ```
    [
        {{
            "destination": "City Name",
            "country": "Country Name"
        }},
        ...
    ]
    ```
    Only return the JSON array, no other text."""

    resp = llm.inference(prompt)
    # Parse the response
    suggestions = json.loads(resp[resp.find("["):resp.find("]")+1])
    return suggestions

def check_date_within_forecast_range(start_date: str, max_days: int = 14) -> bool:
    """
    Check if the start date is within the forecast range (default 14 days)
    """
    start = datetime.strptime(start_date, "%Y-%m-%d")
    today = datetime.now()
    days_difference = (start - today).days
    return 0 <= days_difference <= max_days

import requests
from typing import Dict
def get_weather_forecast(place: str, start_date: str, end_date: str, api_key: str) -> Dict:
    """
    Fetch daily weather forecast for a given place starting from start_date.
    Always fetches 14 days of forecast if available.
    Returns status to indicate if date is within forecast range or needs LLM response.
    """
    # First check if the date is within forecast range
    if not check_date_within_forecast_range(start_date):
        return {
            "status": "use_llm",
            "message": "Date is beyond 14-day forecast range, use LLM suggestion"
        }
    
    url = f"https://api.weatherapi.com/v1/forecast.json"
    
    params = {
        "key": api_key,
        "q": place,
        "days": 14  # Always fetch max available forecast
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        forecasts = []

        for day in data.get("forecast", {}).get("forecastday", []):
            if day["date"] > end_date:
                return {
                    "status": "success",
                    "data": forecasts
                }
            if day["date"] >= start_date:
                forecasts.append({
                    "date": day["date"],
                    "temp_max": day["day"]["maxtemp_c"],
                    "temp_min": day["day"]["mintemp_c"],
                    "conditions": day["day"]["condition"]["text"],
                    "humidity": day["day"]["avghumidity"],
                    "rain_chance": day["day"]["daily_chance_of_rain"]
                })
        return {
            "status": "success",
            "data": forecasts
        }
    except requests.RequestException as e:
        return {
            "status": "error",
            "message": f"Weather API error: {str(e)}"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}"
        }

# resp = get_weather_forecast("London", "2025-09-22", "2025-09-26", "e0c09be496724bccbe7140349252109")

def get_travel_destination(start_date: str, end_date: str, budget: float, api_key: str) -> Dict:
    """
    Get travel recommendations in two steps:
    1. Get potential destinations based on budget and dates
    2. If dates within 14 days, analyze weather for each place to recommend the best one
    """
    # First get destination suggestions
    suggested_places = get_llm_suggestions(budget, start_date, end_date)
    
    # Check if dates are within forecast range
    if not check_date_within_forecast_range(start_date):
        # If beyond 14 days, return suggestions as is
        return suggested_places
    
    # For dates within 14 days, get weather for each place
    weather_data = {}
    for place in suggested_places:
        location = f"{place['destination']}, {place['country']}"
        weather_result = get_weather_forecast(location, start_date, end_date, api_key)
        
        if weather_result["status"] == "success":
            weather_data[location] = weather_result["data"]
    
    # If we got weather data, let LLM analyze and pick the best destination
    if weather_data:
        # Create weather summary for each place
        weather_summary = "Weather conditions for each destination:\n\n"
        for location, forecasts in weather_data.items():
            weather_summary += f"{location}:\n"
            for day in forecasts:
                weather_summary += f"- {day['date']}: {day['conditions']}, {day['temp_min']}°C to {day['temp_max']}°C, {day['rain_chance']}% chance of rain\n"
            weather_summary += "\n"
        
        prompt = f"""Based on the weather forecasts for different destinations:

{weather_summary}

Travel Dates: {start_date} to {end_date}

Analyze the weather conditions and recommend the best destination to visit during these dates.
Consider factors like temperature, rain probability, and overall conditions.
Return the suggestions in order of preference (best first).

Return the response in this exact JSON format:
[
    {{"destination": "City Name", "country": "Country Name"}}
]

Order the destinations from best to worst weather conditions.
Only return the JSON array, no other text."""
        
        response = llm.inference(prompt)
        # Parse and return the reordered suggestions
        return json.loads(response[response.find("["):response.find("]")+1])[0]
    
    # If we couldn't get weather data, return original suggestions
    return suggested_places