import os
import json
import asyncio
from llm import LLM
from dotenv import load_dotenv

from utils import get_data_from_url
from hotel_search import search_hotels
from google_search import GoogleSearch
from flight_search import search_flights, display_flights

load_dotenv()

async def itinerary(destination, start_date, end_date, budget_per_person, travel_style="balanced", flights_info=None):
    gs = GoogleSearch()
    llm = LLM(os.getenv("api_base"), os.getenv("deployment_name"), os.getenv("api_version"))
    results = {}
    search_queries = [f"Must visit places in {destination}", f"Crowd favourite places in {destination}", f"Off beat places in {destination}", f"Best food, drinks, restaurants to try in {destination}", f"Best shopping places in {destination}"]
    for query in search_queries:
        print("Querying:", query)
        gs.search(query)
        first_link = gs.get_first_link()
        web_content = await get_data_from_url(first_link)
        print("Web content extracted")
        prompt = f"""Search Query: {query}
        Webpage Content: {web_content}
        Extract the relevant information from the webpage content based on the search query.

        If possible extract the cost per person for each activity or place mentioned in the content.

        If there is no webpage content found, you can use your own knowledge to answer the query.
        """
        query_result = llm.inference(prompt)
        # print(result)
        print("LLM call ended")
        results[query] = query_result
    
    prompt = f"""
    You are an excellent trip planner who is expert in creating detailed itineraries tailored to customer's need.

    Based on the following information, create a detailed itinerary grouping the activities and places to visit for each day.

    Try to include the places close to each other in the same day.

    Information:
    Destination: {destination}
    Start Date: {start_date}
    End Date: {end_date}
    Budget per person: {budget_per_person}
    Travel style: {travel_style}
    Flights Info: {flights_info}
    {results}
    
    At the end, provide additional tips, must try food, sweets and beverages and summary of the total cost per person for the entire trip.

    Also include the list of other important information like local transport, local customs and traditions etc.

    Also include other famous places/activities which can be added to the itinerary based on user's feedback.

    You are allowed to use knowledge of your own in addition to the information provided to create the itinerary.
    """

    final_itinerary = llm.inference(prompt)
    print("Final Itinerary created")
    print(final_itinerary)

def extract_info():
    llm = LLM(os.getenv("api_base"), os.getenv("deployment_name"), os.getenv("api_version"))
    required_fields = ["source", "destination", "start_date", "end_date", "number_of_adults", "budget_per_person", "number_of_children", "travel_style"]
    collected_info = {}
    conversation = []
    while True:
        # Ask user for input
        user_input = input("Please enter your request: ")
        prompt = f"""
        You are a data extraction agent. Your task is to extract the following fields from user input: {', '.join(required_fields)}.

        User Input: {user_input}

        Response Format:
        ```
        {{
            "source": "value",
            "destination": "value",
            "start_date": "value",
            "end_date": "value",
            "number_of_adults": "value",
            "budget_per_person": "value",
            "number_of_children": "value",
            "travel_style": "value"
        }}  
        ```

        If a field is not mentioned in the user input, do not include it in your response.
        
        Any response other than this format will be rejected by the system.
        """
        conversation.append({"role": "user", "content": prompt})
        # Use LLM to extract info (simulate with a dict for now)
        info = llm.inference(conversation)  # Should return a dict with extracted fields
        conversation.append({"role": "assistant", "content": info})
        info = info[info.find('{'):info.find("}") + 1]
        print(info)
        info = json.loads(info)

        # Update collected_info with new info
        collected_info.update({k: v for k, v in info.items() if v})

        # Find missing fields
        missing = [field for field in required_fields if field not in collected_info or not collected_info[field]]
        if not missing:
            print("All required information collected:", collected_info)
            break
        else:
            llm_resp = f"Missing information: {', '.join(missing)}. Please provide these."
            conversation.append({"role": "assistant", "content": llm_resp})
            print(llm_resp)
    return collected_info

def get_flights_info(source, destination, start_date, end_date):
    llm = LLM(os.getenv("api_base"), os.getenv("deployment_name"), os.getenv("api_version"))
    prompt = f"""What is the short form of {source} airport to book flight from API? Just reply with the short form, nothing else. If there is no aiport, reply with 'N/A'."""
    source_code = llm.inference(prompt)
    if source_code.strip().upper() == "N/A":
        print(f"No airport found for source: {source}")
        return []
    destination_code = llm.inference(prompt.replace(source, destination))
    if destination_code.strip().upper() == "N/A":
        print(f"No airport found for destination: {destination}")
        return []
    prompt = f"""Convert the following date in YYYY-MM-DD format: {start_date}. Just reply with the date, nothing else. Assume that the current year is 2025"""
    start_date = llm.inference(prompt)
    prompt = f"""Convert the following date in YYYY-MM-DD format: {end_date}. Just reply with the date, nothing else. Assume that the current year is 2025"""
    end_date = llm.inference(prompt)
    start_flights = search_flights(source_code.strip(), destination_code.strip(), start_date)
    end_flights = search_flights(source_code.strip(), destination_code.strip(), end_date)
    return {"start_flights": start_flights, "end_flights": end_flights}

def find_best_flight(flights, budget_per_person, travel_style="balanced"):
    llm = LLM(os.getenv("api_base"), os.getenv("deployment_name"), os.getenv("api_version"))
    prompt = f"""
    You are a flight booking assistant. Your task is to find the best flight based on user's budge and travel style.
    
    Budget per person: {budget_per_person}
    Travel style: {travel_style}

    Here are the available flights:
    {json.dumps(flights)}

    The best flight depends on both budget and travel style. For example, 
    - if the travel style is "economy", prioritize cheaper flights even if they have longer durations, off timings or more stops.
    - if the travel style is "luxury", prioritize shorter durations, better timings and fewer stops even if they are more expensive.
    - if the travel style is "balanced", find a good compromise between cost and convenience.

    Based on the above criteria, select the best flight and provide the details in the following format:
    ```
    {{
        "ongoing_flight": {{
            "airline": "value",
            "price": "value",
            "duration": "value",
            "stops": "value",
            "departure": "value",
            "arrival": "value",
            "travel_class": "value"
        }},
        "return_flight": {{
            "airline": "value",
            "price": "value",
            "duration": "value",
            "stops": "value",
            "departure": "value",
            "arrival": "value",
            "travel_class": "value"
        }}
    }}
    ```

    Any response other than this format will be rejected by the system.
    """
    resp = llm.inference(prompt)
    resp = resp[resp.find('{'):resp.rfind("}") + 1]
    return resp

def get_hotels_info(destination, start_date, end_date, number_of_adults, number_of_children):
    llm= LLM(os.getenv("api_base"), os.getenv("deployment_name"), os.getenv("api_version"))
    prompt = f"""Convert the following date in YYYY-MM-DD format: {start_date}. Just reply with the date, nothing else. Assume that the current year is 2025"""
    start_date = llm.inference(prompt)
    prompt = f"""Convert the following date in YYYY-MM-DD format: {end_date}. Just reply with the date, nothing else. Assume that the current year is 2025"""
    end_date = llm.inference(prompt)
    children_ages = "8,"*int(number_of_children)
    children_ages = children_ages[:-1]
    hotels = search_hotels(
        location=destination,
        check_in_date=start_date,
        check_out_date=end_date,
        adults=int(number_of_adults),
        children=int(number_of_children),
        children_ages=children_ages
    )
    return hotels

def get_best_hotels(hotels, budget_per_person, travel_style="balanced"):
    llm = LLM(os.getenv("api_base"), os.getenv("deployment_name"), os.getenv("api_version"))
    prompt = f"""
    You are a hotel booking assistant. Your task is to find the best hotel based on user's budget and travel style.

    Budget per person: {budget_per_person}
    Travel style: {travel_style}

    Here are the available hotels:
    {json.dumps(hotels)}

    The best hotel depends on both budget and travel style. For example,
    - if the travel style is "economy", prioritize cheaper hotels even if they have fewer amenities or less desirable locations.
    - if the travel style is "luxury", prioritize hotels with more amenities, better locations, and higher ratings even if they are more expensive.
    - if the travel style is "balanced", find a good compromise between cost and quality.

    Based on the above criteria, select the best hotel and provide the details in the following format:
    ```
    {{
        "hotel": {{
            "name": "value",
            "price": "value",
            "rating": "value",
            "location": "value",
            "amenities": "value"
        }}
    }}
    ```

    Any response other than this format will be rejected by the system.
    """
    resp = llm.inference(prompt)
    resp = resp[resp.find('{'):resp.rfind("}") + 1]
    return resp

async def get_user_info():
    # Extract user information
    collected_info = extract_info()

    # Extract the flights information
    flights_info = get_flights_info(collected_info["source"], collected_info["destination"], collected_info["start_date"], collected_info["end_date"])
    best_flights = find_best_flight(flights_info, collected_info["budget_per_person"], travel_style="balanced")

    # Extract the hotels information
    hotels_info = get_hotels_info(collected_info["destination"], collected_info["start_date"], collected_info["end_date"], collected_info["number_of_adults"], collected_info["number_of_children"])
    best_hotels = get_best_hotels(hotels_info, collected_info["budget_per_person"], travel_style="balanced")

    # Create the itinerary
    await itinerary(collected_info["destination"], collected_info["start_date"], collected_info["end_date"], collected_info["budget_per_person"], best_flights, best_hotels)

asyncio.run(get_user_info())