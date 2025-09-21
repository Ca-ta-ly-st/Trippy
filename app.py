import streamlit as st
import asyncio
import time
from backend import TravelPlannerBackend

# Configure Streamlit page
st.set_page_config(
    page_title="Trippy - AI Travel Planner",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

def initialize_session_state():
    """Initialize session state variables"""
    if 'backend' not in st.session_state:
        st.session_state.backend = TravelPlannerBackend()
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'current_stage' not in st.session_state:
        st.session_state.current_stage = "collecting_info"
    if 'flights_info' not in st.session_state:
        st.session_state.flights_info = None
    if 'hotels_info' not in st.session_state:
        st.session_state.hotels_info = None
    if 'itinerary_ready' not in st.session_state:
        st.session_state.itinerary_ready = False

def reset_session():
    """Reset the entire session"""
    st.session_state.backend.reset_session()
    st.session_state.messages = []
    st.session_state.current_stage = "collecting_info"
    st.session_state.flights_info = None
    st.session_state.hotels_info = None
    st.session_state.itinerary_ready = False

def display_chat_messages():
    """Display chat messages"""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

def add_message(role, content):
    """Add a message to the chat"""
    st.session_state.messages.append({"role": role, "content": content})

def display_collected_info():
    """Display collected information in sidebar"""
    st.sidebar.header("📋 Collected Information")
    
    if st.session_state.backend.collected_info:
        for key, value in st.session_state.backend.collected_info.items():
            readable_key = key.replace("_", " ").title()
            st.sidebar.text(f"{readable_key}: {value}")
    else:
        st.sidebar.text("No information collected yet")
    
    # Show missing fields
    missing = st.session_state.backend.get_missing_fields()
    if missing:
        st.sidebar.header("⚠️ Missing Information")
        for field in missing:
            readable_field = field.replace("_", " ").title()
            st.sidebar.text(f"• {readable_field}")

def process_user_input(user_input):
    """Process user input and update the conversation"""
    # Add user message to chat
    add_message("user", user_input)
    
    if st.session_state.current_stage == "collecting_info":
        # Extract information from user input
        extracted_info = st.session_state.backend.extract_info_from_input(user_input)
        
        # Check if all information is collected
        if st.session_state.backend.is_info_complete():
            add_message("assistant", "Great! I have all the information I need. Let me search for flights and hotels for you...")
            st.session_state.current_stage = "searching_flights_hotels"
            st.rerun()
        else:
            # Ask for missing information
            missing_msg = st.session_state.backend.get_missing_fields_message()
            add_message("assistant", missing_msg)

def search_flights_and_hotels():
    """Search for flights and hotels"""
    with st.spinner("Searching for flights..."):
        flights_info = st.session_state.backend.get_flights_info()
        if "error" in flights_info:
            add_message("assistant", f"⚠️ Flight search error: {flights_info['error']}")
            st.session_state.flights_info = None
        else:
            st.session_state.flights_info = flights_info
            add_message("assistant", "✅ Found flight options!")
    
    with st.spinner("Searching for hotels..."):
        hotels_info = st.session_state.backend.get_hotels_info()
        if isinstance(hotels_info, dict) and "error" in hotels_info:
            add_message("assistant", f"⚠️ Hotel search error: {hotels_info['error']}")
            st.session_state.hotels_info = None
        else:
            st.session_state.hotels_info = hotels_info
            add_message("assistant", "✅ Found hotel options!")
    
    # Find best options
    best_flights = None
    best_hotels = None
    
    if st.session_state.flights_info and "error" not in st.session_state.flights_info:
        with st.spinner("Finding best flights..."):
            best_flights = st.session_state.backend.find_best_flight(st.session_state.flights_info)
            if "error" not in str(best_flights):
                add_message("assistant", "✅ Selected best flights based on your preferences!")
    
    if st.session_state.hotels_info and "error" not in str(st.session_state.hotels_info):
        with st.spinner("Finding best hotels..."):
            best_hotels = st.session_state.backend.get_best_hotels(st.session_state.hotels_info)
            if "error" not in str(best_hotels):
                add_message("assistant", "✅ Selected best hotels based on your preferences!")
    
    add_message("assistant", "Now let me create your personalized itinerary...")
    st.session_state.current_stage = "creating_itinerary"
    st.session_state.best_flights = best_flights
    st.session_state.best_hotels = best_hotels

def create_itinerary():
    """Create the final itinerary"""
    with st.spinner("Creating your personalized itinerary... This may take a few minutes."):
        itinerary = st.session_state.backend.create_itinerary(
            flights_info=getattr(st.session_state, 'best_flights', None),
            hotels_info=getattr(st.session_state, 'best_hotels', None)
        )
        
        add_message("assistant", f"🎉 **Your Personalized Travel Itinerary is Ready!**\n\n{itinerary}")
        st.session_state.itinerary_ready = True
        st.session_state.current_stage = "completed"

def main():
    """Main Streamlit app"""
    initialize_session_state()
    
    # Header
    st.title("✈️ Trippy - AI Travel Planner")
    st.markdown("Your intelligent travel companion for planning the perfect trip!")
    
    # Sidebar
    with st.sidebar:
        st.header("🎯 Travel Planner")
        
        if st.button("🔄 Start New Trip", use_container_width=True):
            reset_session()
            st.rerun()
        
        st.markdown("---")
        display_collected_info()
        
        # Progress indicator
        st.markdown("---")
        st.header("📊 Progress")
        if st.session_state.current_stage == "collecting_info":
            st.progress(25, "Collecting information...")
        elif st.session_state.current_stage == "searching_flights_hotels":
            st.progress(50, "Searching flights & hotels...")
        elif st.session_state.current_stage == "creating_itinerary":
            st.progress(75, "Creating itinerary...")
        elif st.session_state.current_stage == "completed":
            st.progress(100, "Completed!")
    
    # Main chat interface
    st.header("💬 Chat with Trippy")
    
    # Display chat messages
    display_chat_messages()
    
    # Welcome message
    if not st.session_state.messages:
        welcome_msg = """
        👋 Hello! I'm Trippy, your AI travel planner. I'll help you create the perfect travel itinerary!
        
        To get started, please tell me about your travel plans. I need to know:
        
        🏠 **Departure location** (where you're traveling from)
        🎯 **Destination** (where you want to go)
        📅 **Travel dates** (start and end dates)
        👥 **Number of travelers** (adults and children)
        💰 **Budget per person**
        🎨 **Travel style** (economy, balanced, or luxury)
        
        You can provide all this information at once, or we can go step by step. Just start by telling me about your trip!
        """
        add_message("assistant", welcome_msg)
        st.rerun()
    
    # Handle different stages
    if st.session_state.current_stage == "searching_flights_hotels":
        search_flights_and_hotels()
        st.rerun()
    
    elif st.session_state.current_stage == "creating_itinerary":
        # Run synchronous function
        create_itinerary()
        st.rerun()
    
    # Chat input
    if st.session_state.current_stage in ["collecting_info"] or (st.session_state.current_stage == "completed" and st.session_state.itinerary_ready):
        if prompt := st.chat_input("Type your message here..."):
            if st.session_state.current_stage == "collecting_info":
                with st.spinner("Processing your input..."):
                    process_user_input(prompt)
                    st.rerun()
            elif st.session_state.current_stage == "completed":
                # Handle follow-up questions about the itinerary
                add_message("user", prompt)
                
                # Use LLM to answer questions about the itinerary
                context = "Based on the travel itinerary I created for you, " + prompt
                response = st.session_state.backend.llm.inference(context)
                add_message("assistant", response)
                st.rerun()
    
    # Display helpful information
    if st.session_state.current_stage == "completed":
        st.markdown("---")
        st.info("💡 **Tip**: You can ask me questions about your itinerary or request modifications!")

if __name__ == "__main__":
    main()
