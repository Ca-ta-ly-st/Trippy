import os
import json
import asyncio
from llm import LLM
from dotenv import load_dotenv

from utils import get_data_from_url
from hotel_search import search_hotels
from google_search import GoogleSearch
from flight_search import search_flights, display_flights
from weather import get_travel_destination

load_dotenv()

class TravelPlannerBackend:
    def __init__(self):
        self.llm = LLM(os.getenv("api_base"), os.getenv("deployment_name"), os.getenv("api_version"))
        self.required_fields = ["source", "destination", "start_date", "end_date", "number_of_adults", "budget_per_person", "number_of_children", "travel_style"]
        self.collected_info = {}
        self.conversation_history = []

    def extract_info_from_input(self, user_input):
        """Extract travel information from user input using LLM"""
        prompt = f"""
        You are a data extraction agent. Your task is to extract the following fields from user input: {', '.join(self.required_fields)}.

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
        
        # Use the conversation history for context
        conversation = self.conversation_history + [{"role": "user", "content": prompt}]
        info_response = self.llm.inference(conversation)
        
        # Extract JSON from response
        try:
            info_start = info_response.find('{')
            info_end = info_response.rfind('}') + 1
            if info_start != -1 and info_end != 0:
                info_json = info_response[info_start:info_end]
                info = json.loads(info_json)
                
                # Update collected_info with new info
                self.collected_info.update({k: v for k, v in info.items() if v})
                
                # Add to conversation history
                self.conversation_history.append({"role": "user", "content": user_input})
                self.conversation_history.append({"role": "assistant", "content": info_response})
                
                return info
        except (json.JSONDecodeError, ValueError):
            pass
        
        return {}

    def get_missing_fields(self):
        """Get list of missing required fields"""
        return [field for field in self.required_fields if field not in self.collected_info or not self.collected_info[field]]

    def is_info_complete(self):
        """Check if all required information is collected"""
        return len(self.get_missing_fields()) == 0

    def get_missing_fields_message(self):
        """Get a user-friendly message about missing fields"""
        missing = self.get_missing_fields()
        if not missing:
            return "All required information collected!"
        
        field_names = {
            "source": "departure city/location",
            "destination": "destination city/country",
            "start_date": "start date of travel",
            "end_date": "end date of travel",
            "number_of_adults": "number of adults",
            "budget_per_person": "budget per person",
            "number_of_children": "number of children",
            "travel_style": "travel style (economy/balanced/luxury)"
        }
        
        missing_readable = [field_names.get(field, field) for field in missing]
        return f"I still need the following information: {', '.join(missing_readable)}. Please provide these details."

    def get_flights_info(self):
        """Get flight information for the trip"""
        try:
            source = self.collected_info["source"]
            destination = self.collected_info["destination"]
            start_date = self.collected_info["start_date"]
            end_date = self.collected_info["end_date"]
            
            # Get airport codes
            prompt = f"""What is the short form of {source} airport to book flight from API? Just reply with the short form, nothing else. If there is no airport, reply with 'N/A'."""
            source_code = self.llm.inference(prompt)
            
            if source_code.strip().upper() == "N/A":
                return {"error": f"No airport found for source: {source}"}
                
            destination_code = self.llm.inference(prompt.replace(source, destination))
            if destination_code.strip().upper() == "N/A":
                return {"error": f"No airport found for destination: {destination}"}
            
            # Convert dates
            prompt = f"""Convert the following date in YYYY-MM-DD format: {start_date}. Just reply with the date, nothing else. Assume that the current year is 2025"""
            formatted_start_date = self.llm.inference(prompt)
            
            prompt = f"""Convert the following date in YYYY-MM-DD format: {end_date}. Just reply with the date, nothing else. Assume that the current year is 2025"""
            formatted_end_date = self.llm.inference(prompt)
            
            # Search flights
            start_flights = search_flights(source_code.strip(), destination_code.strip(), formatted_start_date.strip())
            end_flights = search_flights(destination_code.strip(), source_code.strip(), formatted_end_date.strip())
            
            return {"start_flights": start_flights, "end_flights": end_flights}
            
        except Exception as e:
            return {"error": f"Error getting flight information: {str(e)}"}

    def find_best_flight(self, flights_info):
        """Find the best flight based on budget and travel style"""
        try:
            budget_per_person = self.collected_info["budget_per_person"]
            travel_style = self.collected_info.get("travel_style", "balanced")
            
            prompt = f"""
            You are a flight booking assistant. Your task is to find the best flight based on user's budget and travel style.
            
            Budget per person: {budget_per_person}
            Travel style: {travel_style}

            Here are the available flights:
            {json.dumps(flights_info)}

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
            resp = self.llm.inference(prompt)
            resp_start = resp.find('{')
            resp_end = resp.rfind('}') + 1
            if resp_start != -1 and resp_end != 0:
                return json.loads(resp[resp_start:resp_end])
            else:
                return {"error": "Could not parse flight response"}
        except Exception as e:
            return {"error": f"Error finding best flight: {str(e)}"}

    def get_hotels_info(self):
        """Get hotel information for the trip"""
        try:
            destination = self.collected_info["destination"]
            start_date = self.collected_info["start_date"]
            end_date = self.collected_info["end_date"]
            number_of_adults = self.collected_info["number_of_adults"]
            number_of_children = self.collected_info["number_of_children"]
            
            # Convert dates
            prompt = f"""Convert the following date in YYYY-MM-DD format: {start_date}. Just reply with the date, nothing else. Assume that the current year is 2025"""
            formatted_start_date = self.llm.inference(prompt)
            
            prompt = f"""Convert the following date in YYYY-MM-DD format: {end_date}. Just reply with the date, nothing else. Assume that the current year is 2025"""
            formatted_end_date = self.llm.inference(prompt)
            
            children_ages = "8," * int(number_of_children)
            children_ages = children_ages[:-1] if children_ages else ""
            
            hotels = search_hotels(
                location=destination,
                check_in_date=formatted_start_date.strip(),
                check_out_date=formatted_end_date.strip(),
                adults=int(number_of_adults),
                children=int(number_of_children),
                children_ages=children_ages
            )
            return hotels
        except Exception as e:
            return {"error": f"Error getting hotel information: {str(e)}"}

    def get_best_hotels(self, hotels_info):
        """Find the best hotel based on budget and travel style"""
        try:
            budget_per_person = self.collected_info["budget_per_person"]
            travel_style = self.collected_info.get("travel_style", "balanced")
            
            prompt = f"""
            You are a hotel booking assistant. Your task is to find the best hotel based on user's budget and travel style.

            Budget per person: {budget_per_person}
            Travel style: {travel_style}

            Here are the available hotels:
            {json.dumps(hotels_info)}

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
            resp = self.llm.inference(prompt)
            resp_start = resp.find('{')
            resp_end = resp.rfind('}') + 1
            if resp_start != -1 and resp_end != 0:
                return json.loads(resp[resp_start:resp_end])
            else:
                return {"error": "Could not parse hotel response"}
        except Exception as e:
            return {"error": f"Error finding best hotel: {str(e)}"}

    def create_itinerary(self, flights_info=None, hotels_info=None):
        """Create detailed itinerary based on collected information"""
        try:
            destination = self.collected_info["destination"]
            start_date = self.collected_info["start_date"]
            end_date = self.collected_info["end_date"]
            budget_per_person = self.collected_info["budget_per_person"]
            travel_style = self.collected_info.get("travel_style", "balanced")
            
            gs = GoogleSearch()
            results = {}
            
            search_queries = [
                f"Must visit places in {destination}",
                f"Crowd favourite places in {destination}",
                f"Off beat places in {destination}",
                f"Best food, drinks, restaurants to try in {destination}",
                f"Best shopping places in {destination}"
            ]
            
            for query in search_queries:
                try:
                    gs.search(query)
                    first_link = gs.get_first_link()
                    print(first_link)
                    # Create a new event loop for this specific async call
                    web_content = asyncio.run(get_data_from_url(first_link))
                    
                    prompt = f"""Search Query: {query}
                    Webpage Content: {web_content}
                    Extract the relevant information from the webpage content based on the search query.

                    If possible extract the cost per person for each activity or place mentioned in the content.

                    If there is no webpage content found, you can use your own knowledge to answer the query.
                    """
                    query_result = self.llm.inference(prompt)
                    results[query] = query_result
                except Exception as e:
                    results[query] = f"Error retrieving information: {str(e)}"
            # Convert dates
            prompt = f"""Convert the following date in YYYY-MM-DD format: {start_date}. Just reply with the date, nothing else. Assume that the current year is 2025"""
            formatted_start_date = self.llm.inference(prompt)
            
            prompt = f"""Convert the following date in YYYY-MM-DD format: {end_date}. Just reply with the date, nothing else. Assume that the current year is 2025"""
            formatted_end_date = self.llm.inference(prompt)
            best_destination = get_travel_destination(formatted_start_date, formatted_end_date, budget_per_person, os.getenv("WEATHER_KEY"))
            
            prompt = f"""
            You are an excellent trip planner who is expert in creating detailed itineraries tailored to customer's need.

            Based on the following information, create a detailed itinerary grouping the activities and places to visit for each day.

            Try to include the places close to each other in the same day.

            Information:
            ```
            Destination: {destination}
            Start Date: {start_date}
            End Date: {end_date}
            Budget per person: {budget_per_person}
            Travel style: {travel_style}
            Flights Info: {flights_info}
            Hotels Info: {hotels_info}
            {results}
            ```
            
            The budget mention by the user is in INR (Indian Rupees).
            The cost of flights and hotels provided to you are in USD (US Dollars). Assume 1 USD = 83 INR for conversion.
            
            At the end of itinerary:
            - Make a section to provide additional tips, must try food, sweets and beverages.
            - Provide a summary of the total cost per person for the entire trip.
            - Include the list of other important information like local transport, local customs and traditions etc.
            - Include other famous places/activities which can be added to the itinerary based on user's feedback.
            - Include the flight details and hotel details in the itinerary.

            At the very end, also include that according to the dates, weather and budget, the best destination to visit is {best_destination}.
            You are allowed to use knowledge of your own in addition to the information provided to create the itinerary.
            """

            final_itinerary = self.llm.inference(prompt)
            return final_itinerary
            
        except Exception as e:
            return f"Error creating itinerary: {str(e)}"

    def reset_session(self):
        """Reset the session data"""
        self.collected_info = {}
        self.conversation_history = []
