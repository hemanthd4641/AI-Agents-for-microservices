import os
import uvicorn
import asyncio
import logging
import requests
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
# from serpapi import GoogleSearch  # Removed SerpAPI
from crewai import Agent, Task, Crew, Process, LLM
from datetime import datetime
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()

# Load API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SERP_API_KEY = os.getenv("SERPER_API_KEY")
UNSPLASH_API_KEY = os.getenv("UNSPLASH_API_KEY")
TICKETMASTER_API_KEY = os.getenv("TICKETMASTER_API_KEY")

# Initialize Logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ==========================
#  Initialize Groq (LLM)
# ==========================
@lru_cache(maxsize=1)
def initialize_llm():
    """Initialingand caching LLM instance to avoid repeated initializations."""
    return LLM(
        model="groq/llama-3.1-8b-instant",
        api_key=GROQ_API_KEY
    )

# ==========================
#  Pydantic Models
# ==========================
class FlightRequest(BaseModel):
    origin: str
    destination: str
    outbound_date: str
    return_date: str
    num_people: int = 1
    budget: str = "Moderate"
    food_preference: str = "Any"
    travel_mode: str = "flight"   # "flight", "road", "train", "bus"

class HotelRequest(BaseModel):
    location: str
    check_in_date: str
    check_out_date: str
    num_people: int = 1
    budget: str = "Moderate"
    food_preference: str = "Any"

class ItineraryRequest(BaseModel):
    destination: str
    check_in_date: str
    check_out_date: str
    flights: str
    hotels: str
    num_people: int = 1
    budget: str = "Moderate"
    food_preference: str = "Any"

class FlightInfo(BaseModel):
    airline: str
    price: str
    duration: str
    stops: str
    departure: str
    arrival: str
    travel_class: str
    return_date: str
    airline_logo: str

class HotelInfo(BaseModel):
    name: str
    price: str
    rating: float
    location: str
    link: str

class MapCoordinate(BaseModel):
    name: str
    lat: float
    lon: float

class AIResponse(BaseModel):
    flights: List[FlightInfo] = []
    hotels: List[HotelInfo] = []
    ai_flight_recommendation: str = ""
    ai_hotel_recommendation: str = ""
    weather: str = ""
    ai_weather_recommendation: str = ""
    itinerary: str = ""
    map_coordinates: List[MapCoordinate] = []
    expenses: dict = {}
    culture_guide: str = ""
    destination_images: List[str] = []
    destination_description: str = ""
    live_events: str = ""

# ==========================
#  Initialize FastAPI
# ==========================
app = FastAPI(title="Travel Planning API", version="1.1.0")

# ==========================
#  Fetch Data from Serper.dev
# ==========================
async def run_search(query: str, endpoint: str = "search"):
    """Generic function to run Serper.dev searches asynchronously."""
    url = f"https://google.serper.dev/{endpoint}"
    payload = json.dumps({"q": query})
    headers = {
        'X-API-KEY': SERP_API_KEY,
        'Content-Type': 'application/json'
    }
    try:
        response = await asyncio.to_thread(requests.post, url, headers=headers, data=payload)
        return response.json()
    except Exception as e:
        logger.exception(f"Serper search error: {str(e)}")
        return {"error": str(e)}

# ==========================
#  Fetch Weather from Open-Meteo
# ==========================
async def get_weather(location: str, start_date: str, end_date: str):
    """Fetch coordinates and then get weather forecast from Open-Meteo."""
    logger.info(f"Fetching weather for: {location}")
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1&language=en&format=json"
        geo_res = await asyncio.to_thread(requests.get, geo_url, timeout=10)
        geo_data = geo_res.json()
        
        if not geo_data.get("results"):
            # Try splitting by comma if it's a multi-city string
            main_city = location.split(",")[0].strip()
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={main_city}&count=1&language=en&format=json"
            geo_res = await asyncio.to_thread(requests.get, geo_url, timeout=10)
            geo_data = geo_res.json()

        if not geo_data.get("results"):
            logger.warning(f"Could not find coordinates for {location}")
            return f"Weather forecast unavailable for {location}: location not found."
            
        lat = geo_data["results"][0]["latitude"]
        lon = geo_data["results"][0]["longitude"]
        
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=auto&start_date={start_date}&end_date={end_date}"
        weather_res = await asyncio.to_thread(requests.get, weather_url)
        weather_data = weather_res.json()
        
        if "daily" not in weather_data:
            return "Weather forecast unavailable."
            
        formatted_weather = "**Daily Weather Forecast**:\n\n"
        daily = weather_data["daily"]
        for i in range(len(daily["time"])):
            formatted_weather += (
                f"- **{daily['time'][i]}**: "
                f"High: {daily['temperature_2m_max'][i]}°C | "
                f"Low: {daily['temperature_2m_min'][i]}°C | "
                f"Precip Chance: {daily['precipitation_probability_max'][i]}%\n"
            )
            
        return formatted_weather.strip()
        
    except Exception as e:
        logger.exception(f"Open-Meteo API error: {str(e)}")
        return f"Error fetching weather: {str(e)}"

async def fetch_destination_images(destination: str) -> List[str]:
    """Fetch images using Serper.dev (user has a key for this)."""
    try:
        # Use Serper's image search
        logger.info(f"Fetching images for {destination} via Serper")
        url = "https://google.serper.dev/images"
        payload = json.dumps({"q": f"{destination} landmarks travel", "num": 5})
        headers = {
            'X-API-KEY': SERP_API_KEY,
            'Content-Type': 'application/json'
        }
        response = await asyncio.to_thread(requests.post, url, headers=headers, data=payload, timeout=10)
        data = response.json()
        
        images = [img["imageUrl"] for img in data.get("images", []) if "imageUrl" in img]
        if images:
            return images[:5]
            
        # Fallback to a single reliable placeholder if everything fails
        return ["https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?q=80&w=1000&auto=format&fit=crop"]
    except Exception as e:
        logger.error(f"Image search error: {e}")
        return ["https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?q=80&w=1000&auto=format&fit=crop"]

async def fetch_destination_description(destination: str) -> str:
    """Fetch a short summary from Wikipedia."""
    try:
        # Step 1: Search for the best Wikipedia title
        search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={destination}&format=json&origin=*"
        search_res = await asyncio.to_thread(requests.get, search_url, timeout=10)
        search_data = search_res.json()
        
        if search_data.get("query", {}).get("search"):
            best_title = search_data["query"]["search"][0]["title"]
            # Step 2: Get summary for that title
            summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{best_title.replace(' ', '_')}"
            res = await asyncio.to_thread(requests.get, summary_url, timeout=10)
            if res.status_code == 200:
                data = res.json()
                return data.get("extract", "")
        
        # Fallback to Serper.dev snippet if Wikipedia fails
        logger.info(f"Wikipedia failed for {destination}, trying Serper fallback")
        serper_res = await run_search(f"About {destination} city description")
        if serper_res.get("organic"):
            return serper_res["organic"][0].get("snippet", f"Explore the wonders of {destination}!")
            
        return f"Explore the wonders of {destination}!"
    except Exception as e:
        logger.error(f"Wikipedia/Description error: {e}")
        return f"Welcome to {destination}!"

async def fetch_live_events(city: str, start_date: str, end_date: str) -> str:
    """Fetch live concerts, sports, and festivals from Ticketmaster API."""
    if not TICKETMASTER_API_KEY or TICKETMASTER_API_KEY == "<Your API Key>":
        return ""
    try:
        url = "https://app.ticketmaster.com/discovery/v2/events.json"
        params = {
            "apikey": TICKETMASTER_API_KEY,
            "city": city,
            "startDateTime": f"{start_date}T00:00:00Z",
            "endDateTime": f"{end_date}T23:59:59Z",
            "size": 5,
            "sort": "relevance,desc"
        }
        res = await asyncio.to_thread(requests.get, url, params=params)
        data = res.json()
        events = data.get("_embedded", {}).get("events", [])
        if not events:
            return ""
        
        lines = [f"🎭 **Live Events in {city}:**"]
        for e in events:
            name = e.get("name", "Unknown Event")
            date = e.get("dates", {}).get("start", {}).get("localDate", "TBD")
            venue = e.get("_embedded", {}).get("venues", [{}])[0].get("name", "TBD")
            category = e.get("classifications", [{}])[0].get("segment", {}).get("name", "Event")
            lines.append(f"- **{name}** | {category} | 📅 {date} | 📍 {venue}")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Ticketmaster error: {e}")
        return ""

async def get_location_coordinates(place_name: str, destination: str):
    """Fetch coordinates for a specific place using Open-Meteo Geocoding."""
    try:
        search_query = f"{place_name} {destination}"
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={search_query}&count=1&language=en&format=json"
        geo_res = await asyncio.to_thread(requests.get, geo_url)
        geo_data = geo_res.json()
        
        if geo_data.get("results"):
            return MapCoordinate(
                name=place_name,
                lat=geo_data["results"][0]["latitude"],
                lon=geo_data["results"][0]["longitude"]
            )
        return None
    except Exception as e:
        logger.warning(f"Failed to geocode {place_name}: {str(e)}")
        return None

async def extract_locations_from_itinerary(itinerary: str):
    """Use an LLM to quickly extract key locations from the itinerary."""
    llm_model = initialize_llm()
    extractor_agent = Agent(
        role="Location Extractor",
        goal="Extract the names of hotels, restaurants, and attractions from the itinerary.",
        backstory="A precise data extractor.",
        llm=llm_model,
        verbose=False
    )
    extractor_task = Task(
        description=f"Extract the top 5-8 specific places (hotels, restaurants, landmarks) mentioned in this itinerary. Return ONLY a comma-separated list of their names, nothing else.\n\nItinerary:\n{itinerary}",
        agent=extractor_agent,
        expected_output="Comma-separated list of place names"
    )
    crew = Crew(agents=[extractor_agent], tasks=[extractor_task], process=Process.sequential, verbose=False)
    
    try:
        results = await asyncio.to_thread(crew.kickoff)
        if hasattr(results, 'outputs') and results.outputs:
            output = str(results.outputs[0])
        else:
            output = str(results)
            
        places = [p.strip() for p in output.split(",") if p.strip() and len(p.strip()) > 2]
        return places[:8]
    except:
        return []

async def estimate_trip_expenses(flights_text: str, hotels_text: str, itinerary: str, num_people: int, days: int, budget: str):
    """Use an LLM to estimate the total trip expenses based on gathered data."""
    llm_model = initialize_llm()
    analyst_agent = Agent(
        role="Financial Analyst",
        goal="Estimate the total cost of the trip in USD.",
        backstory="An expert financial planner who accurately breaks down travel expenses into specific categories.",
        llm=llm_model,
        verbose=False
    )
    
    prompt = f"""
    Analyze the following travel data to estimate the total trip cost in USD.
    
    Trip Details:
    - Group Size: {num_people}
    - Duration: {days} days
    - Budget Preference: {budget}
    
    Flight Data:
    {flights_text}
    
    Hotel Data:
    {hotels_text}
    
    Itinerary:
    {itinerary}
    
    Return exactly a valid JSON object with the following keys representing the estimated total cost in USD for the entire group:
    - "Flights"
    - "Accommodation"
    - "Food"
    - "Activities"
    
    Do not include any other text, only the JSON object. Ensure the values are numbers (integers or floats).
    """
    
    analyst_task = Task(
        description=prompt,
        agent=analyst_agent,
        expected_output="Valid JSON object with keys: Flights, Accommodation, Food, Activities"
    )
    
    crew = Crew(agents=[analyst_agent], tasks=[analyst_task], process=Process.sequential, verbose=False)
    
    try:
        results = await asyncio.to_thread(crew.kickoff)
        output = results.outputs[0] if hasattr(results, 'outputs') and results.outputs else str(results)
        
        # Clean the output to ensure valid JSON
        output = output.replace('```json', '').replace('```', '').strip()
        # Find the first { and last }
        start = output.find('{')
        end = output.rfind('}') + 1
        if start != -1 and end != 0:
            output = output[start:end]
            
        expenses = json.loads(output)
        return expenses
    except Exception as e:
        logger.error(f"Error estimating expenses: {e}")
        # Default fallback so the chart still shows something
        return {"Flights": 500, "Accommodation": 800, "Food": 400, "Activities": 300}

async def generate_culture_guide(destination: str):
    """Use an LLM to generate a local culture and language guide."""
    llm_model = initialize_llm()
    expert_agent = Agent(
        role="Local Culture & Language Expert",
        goal=f"Provide a survival guide for travelers visiting {destination}.",
        backstory="A seasoned local guide who knows all the cultural nuances, etiquette, and essential language phrases for the region.",
        llm=llm_model,
        verbose=False
    )
    
    prompt = f"""
    Create a 'Local Survival Guide' for a traveler visiting {destination}.
    
    The guide must include two sections:
    1. **🗣️ Mini Phrasebook**: 10 essential phrases translated into the primary local language (with English pronunciations in parentheses).
    2. **🤝 Local Etiquette**: 3 to 5 critical rules visitors must know to be respectful (e.g., tipping expectations, dress codes for temples/churches, greetings, social norms).
    
    Format the response in beautiful, clear Markdown.
    """
    
    expert_task = Task(
        description=prompt,
        agent=expert_agent,
        expected_output="Markdown formatted survival guide with phrases and etiquette."
    )
    
    crew = Crew(agents=[expert_agent], tasks=[expert_task], process=Process.sequential, verbose=False)
    
    try:
        results = await asyncio.to_thread(crew.kickoff)
        if hasattr(results, 'outputs') and results.outputs:
            return results.outputs[0]
        elif hasattr(results, 'get'):
            return results.get("Local Culture & Language Expert", "")
        else:
            return str(results)
    except Exception as e:
        logger.error(f"Error generating culture guide: {e}")
        return ""

async def search_flights(flight_request: FlightRequest):
    """Fetch flight details using Serper.dev."""
    logger.info(f"Searching flights: {flight_request.origin} to {flight_request.destination}")
    
    query = f"flights from {flight_request.origin} to {flight_request.destination} on {flight_request.outbound_date} return {flight_request.return_date}"
    search_results = await run_search(query)

    if "error" in search_results:
        return {"error": search_results["error"]}

    # Organic results as fallback for flights in Serper
    organic = search_results.get("organic", [])
    formatted_flights = []
    
    for i, result in enumerate(organic[:3]):
        formatted_flights.append(FlightInfo(
            airline=result.get("title", "Flight Info"),
            price="Check Link",
            duration="See details",
            stops="Check site",
            departure=flight_request.outbound_date,
            arrival=flight_request.destination,
            travel_class="Economy",
            return_date=flight_request.return_date,
            airline_logo=""
        ))

    return formatted_flights


async def search_hotels(hotel_request: HotelRequest):
    """Fetch hotel information from Serper.dev."""
    logger.info(f"Searching hotels for: {hotel_request.location}")

    query = f"hotels in {hotel_request.location} check-in {hotel_request.check_in_date} check-out {hotel_request.check_out_date}"
    search_results = await run_search(query, endpoint="places")

    if "error" in search_results:
        return {"error": search_results["error"]}

    places = search_results.get("places", [])
    formatted_hotels = []
    for hotel in places[:5]:
        formatted_hotels.append(HotelInfo(
            name=hotel.get("title", "Unknown Hotel"),
            price="Check Link",
            rating=float(hotel.get("rating", 0.0)),
            location=hotel.get("address", "N/A"),
            link=f"https://www.google.com/search?q={hotel.get('title')}"
        ))

    return formatted_hotels

# ==============================================
#  Format Data for AI
# ==============================================
def format_travel_data(data_type, data):
    """Generic formatter for both flight and hotel data."""
    if not data:
        return f"No {data_type} available."

    if data_type == "flights":
        formatted_text = "**Available flight options**:\n\n"
        for i, flight in enumerate(data):
            formatted_text += (
                f"**Flight {i + 1}:**\n"
                f"✈️ **Airline:** {flight.airline}\n"
                f" ₹ **Price:** ${flight.price}\n"
                f"⏱️ **Duration:** {flight.duration}\n"
                f"🛑 **Stops:** {flight.stops}\n"
                f"🕔 **Departure:** {flight.departure}\n"
                f"🕖 **Arrival:** {flight.arrival}\n"
                f"💺 **Class:** {flight.travel_class}\n\n"
            )
    elif data_type == "hotels":
        formatted_text = "**Available Hotel Options**:\n\n"
        for i, hotel in enumerate(data):
            formatted_text += (
                f"**Hotel {i + 1}:**\n"
                f"🏨 **Name:** {hotel.name}\n"
                f" ₹ **Price:** ₹{hotel.price}\n"
                f"⭐ **Rating:** {hotel.rating}\n"
                f"📍 **Location:** {hotel.location}\n"
                f"🔗 **More Info:** [Link]({hotel.link})\n\n"
            )
    else:
        return "Invalid data type."

    return formatted_text.strip()


# =======================
#  Search & Utility Functions
# =======================
# (Removed duplicate run_search)

async def get_coordinates(city: str) -> Optional[tuple[float, float]]:
    """Get lat/lon for a city using Open-Meteo Geocoding API."""
    try:
        url = "https://geocoding-api.open-meteo.com/v1/search"
        params = {"name": city, "count": 1, "language": "en", "format": "json"}
        response = requests.get(url, params=params)
        data = response.json()
        if data.get("results"):
            res = data["results"][0]
            return float(res["latitude"]), float(res["longitude"])
        
        # Fallback for city, state, country
        simple_city = city.split(",")[0].strip()
        if simple_city != city:
            params["name"] = simple_city
            response = requests.get(url, params=params)
            data = response.json()
            if data.get("results"):
                res = data["results"][0]
                return float(res["latitude"]), float(res["longitude"])
    except:
        pass
    return None

async def get_weather(city: str, start_date: str, end_date: str) -> str:
    """Fetch daily weather forecast using Open-Meteo API."""
    coords = await get_coordinates(city)
    if not coords:
        return f"Weather forecast unavailable for {city}: location not found."
    
    lat, lon = coords
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": ["temperature_2m_max", "temperature_2m_min", "precipitation_probability_max"],
            "timezone": "auto",
            "start_date": start_date,
            "end_date": end_date
        }
        response = requests.get(url, params=params)
        data = response.json()
        
        if "daily" not in data:
            return "Weather forecast unavailable: API error."
            
        daily = data["daily"]
        forecast_lines = [f"Daily Weather Forecast for {city}:"]
        for i in range(len(daily["time"])):
            forecast_lines.append(
                f"{daily['time'][i]}: High: {daily['temperature_2m_max'][i]}°C | "
                f"Low: {daily['temperature_2m_min'][i]}°C | "
                f"Precip Chance: {daily['precipitation_probability_max'][i]}%"
            )
        return "\n".join(forecast_lines)
    except Exception as e:
        logger.error(f"Weather fetch error for {city}: {e}")
        return "Weather forecast unavailable due to an error."

async def fetch_destination_images(city: str) -> List[str]:
    """Fetch city images from Unsplash."""
    if not UNSPLASH_API_KEY:
        return []
    try:
        url = "https://api.unsplash.com/search/photos"
        params = {"query": city, "client_id": UNSPLASH_API_KEY, "per_page": 5, "orientation": "landscape"}
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            return [img["urls"]["regular"] for img in data.get("results", [])]
    except:
        pass
    return []

async def fetch_destination_description(city: str) -> str:
    """Fetch city description from Wikipedia using search to find the best match."""
    try:
        # Search for best matching page
        search_url = "https://en.wikipedia.org/w/api.php"
        search_params = {"action": "query", "list": "search", "srsearch": f"{city} city", "format": "json"}
        search_resp = requests.get(search_url, params=search_params)
        search_data = search_resp.json()
        
        if search_data.get("query", {}).get("search"):
            title = search_data["query"]["search"][0]["title"]
            # Get summary for that page
            sum_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title.replace(' ', '_')}"
            sum_resp = requests.get(sum_url)
            if sum_resp.status_code == 200:
                return sum_resp.json().get("extract", "")
    except:
        pass
    return ""

async def fetch_live_events(city: str, start_date: str, end_date: str) -> str:
    """Fetch live events from Ticketmaster API."""
    if not TICKETMASTER_API_KEY:
        return ""
    try:
        url = "https://app.ticketmaster.com/discovery/v2/events.json"
        params = {
            "apikey": TICKETMASTER_API_KEY,
            "city": city,
            "startDateTime": f"{start_date}T00:00:00Z",
            "endDateTime": f"{end_date}T23:59:59Z",
            "size": 5
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            events = data.get("_embedded", {}).get("events", [])
            if not events: return ""
            
            lines = [f"**Live Events in {city}:**"]
            for e in events:
                name = e.get("name", "Event")
                date = e.get("dates", {}).get("start", {}).get("localDate", "")
                url  = e.get("url", "#")
                lines.append(f"- {name} ({date}) [Tickets]({url})")
            return "\n".join(lines)
    except:
        pass
    return ""

async def extract_locations_from_itinerary(itinerary: str) -> List[str]:
    """Use AI to extract specific names of places/attractions from the itinerary."""
    llm_model = initialize_llm()
    agent = Agent(
        role="Location Extractor",
        goal="Extract a list of specific sightseeing locations/attractions from the provided itinerary.",
        backstory="An AI that specializes in identifying physical landmarks and attractions from text.",
        llm=llm_model,
        verbose=False
    )
    task = Task(
        description=f"Extract only the names of famous places or attractions mentioned in this itinerary. Return them as a comma-separated list of names. Itinerary:\n{itinerary}",
        agent=agent,
        expected_output="Comma-separated list of place names"
    )
    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)
    try:
        results = await asyncio.to_thread(crew.kickoff)
        output = str(results.outputs[0]) if hasattr(results, 'outputs') and results.outputs else str(results)
        return [p.strip() for p in output.split(",") if p.strip()]
    except:
        return []

async def get_location_coordinates(place_name: str, city: str) -> Optional[dict]:
    """Get lat/lon for a specific attraction within a city."""
    try:
        url = "https://geocoding-api.open-meteo.com/v1/search"
        params = {"name": f"{place_name}, {city}", "count": 1, "language": "en", "format": "json"}
        response = requests.get(url, params=params)
        data = response.json()
        if data.get("results"):
            res = data["results"][0]
            return {"name": place_name, "lat": float(res["latitude"]), "lon": float(res["longitude"])}
    except:
        pass
    return None

# =======================
#  AI Analysis Functions
# =======================
async def get_ai_recommendation(data_type, formatted_data):
    """Unified function for getting AI recommendations for both flights and hotels."""
    logger.info(f"Getting {data_type} analysis from AI")
    llm_model = initialize_llm()

    # Agent Configuration based on data type
    if data_type == "flights":
        role = "AI Flight Analyst"
        goal = "Recommend the best flight by assessing price, duration, stops, and convenience."
        backstory = f"An AI specialist that performs detailed comparisons of flight options across multiple criteria."
        description = """
        Based on the information below, evaluate the available flights and recommend the optimal option.:

        **Recommendation Summary:**
        - ** ₹ Price:** Provide a thorough justification for why this flight is the most cost-effective and convenient choice.
        - **⏱️ Duration:** Provide an analysis showing why this flight has a superior total travel time relative to alternatives.
        - **🛑 Stops:** Describe how this flight minimizes layovers while maintaining overall efficiency..
        - **💺 Travel Class:** Provide a detailed assessment of this flight’s comfort features and amenities, highlighting why they outperform alternatives..

        Use the provided flight data as the basis for your recommendation. Be sure to justify your choice using clear reasoning for each attribute. Do not repeat the flight details in your response.
        """
    elif data_type == "hotels":
        role = "AI Hotel Analyst"
        goal = "Analyze hotel options and recommend the best one by considering price, rating, location and amenities."
        backstory = f"AI expert which provides in-depth analysis in comparing hotel options based on multiple factors."
        description = """
        Using the analysis below, recommend the best hotel with a detailed explanation considering price, rating, location, and amenities.

        **AI Hotel Recommendation**
        Based on the analysis below, we recommend the top hotel option::

        **Recommendation Summary:**:
        - **₹ Price:** This hotel represents the most cost-effective option, providing excellent amenities and services relative to its price.
        - **⭐ Rating:** The hotel’s higher rating reflects consistently positive reviews and a higher level of service quality. Compared to alternatives, this indicates a better overall guest experience, making it the optimal selection.
        - **📍 Location: Strategically located near major points of interest, the hotel offers excellent convenience for travelers.
        - **🏨 Amenities: With offerings such as high-speed Wi-Fi, a pool, fitness facilities, and free breakfast, the hotel meets diverse traveler needs. These amenities improve convenience, relaxation, and productivity, making it suitable for families, solo travelers, and business guests alike.

        📝 **Reasoning Requirements**:
        - Each section should provide a clear rationale demonstrating why this hotel is optimal, considering key factors such as price, rating, location, and amenities.
        - Conduct a comparison with the other available options and highlight the factors that make this one the standout choice.
        - Provide well-organized justification to make the recommendation transparent and easy to understand.
        - Ensure the recommendation incorporates multiple criteria so the traveler can weigh all relevant aspects before deciding.
        """
    elif data_type == "weather":
        role = "AI Weather Analyst"
        goal = "Analyze the daily weather forecast for a destination and provide specific packing and activity recommendations."
        backstory = "An expert meteorologist and travel advisor who helps travelers prepare for the elements."
        description = """
        Based on the provided weather forecast, give a short, helpful recommendation for the traveler.

        **Weather Recommendation & Packing Guide:**
        - **🌡️ Overview:** Briefly summarize what the weather will be like during the trip.
        - **🧥 Packing Advice:** Suggest clothing and items to pack based on the temperatures and precipitation chances.
        - **🏃‍♂️ Activity Tips:** Note any days where indoor activities might be preferable due to rain or extreme temps.

        Provide clear and practical advice based on the data.
        """
    else:
        raise ValueError("Invalid data type for AI recommendation")

    analyze_agent = Agent(
        role=role,
        goal=goal,
        backstory=backstory,
        llm=llm_model,
        verbose=False
    )

    analyze_task = Task(
        description=f"{description}\n\nData to analyze:\n{formatted_data}",
        agent=analyze_agent,
        expected_output=f"A concise, data-driven recommendation highlighting the top {data_type} selection according to the analyzed details."
    )

    analyst_crew = Crew(
        agents=[analyze_agent],
        tasks=[analyze_task],
        process=Process.sequential,
        verbose=False
    )

    try:
        crew_results = await asyncio.to_thread(analyst_crew.kickoff)
        if hasattr(crew_results, 'outputs') and crew_results.outputs:
            return crew_results.outputs[0]
        elif hasattr(crew_results, 'get'):
            return crew_results.get(role, f"No {data_type} recommendation available.")
        else:
            return str(crew_results)
    except Exception as e:
        logger.exception(f"Error in AI {data_type} analysis: {str(e)}")
        return f"Unable to generate {data_type} recommendation due to an error."


async def generate_itinerary(destination, flights_text, hotels_text, check_in_date, check_out_date, num_people, budget, food_preference, events_text=""):
    """Generate a detailed travel itinerary based on flight and hotel information."""
    try:
        check_in = datetime.strptime(check_in_date, "%Y-%m-%d")
        check_out = datetime.strptime(check_out_date, "%Y-%m-%d")

        days = (check_out - check_in).days

        llm_model = initialize_llm()

        analyze_agent = Agent(
            role="AI Travel Planner",
            goal="Generate a full itinerary for the traveler, incorporating both flight schedules and hotel accommodations.",
            backstory="AI-driven itinerary planner offering an optimized daily plan including travel logistics, accommodation, and key experiences.",
            llm=llm_model,
            verbose=False
        )

        analyze_task = Task(
            description=f"""
            Based on the following details, create a {days}-day itinerary for the user:

            **Flight Details**:
            {flights_text}

            **Hotel Details**:
            {hotels_text}

            **Destination**: {destination}

            **Travel Dates**: {check_in_date} to {check_out_date} ({days} days)
            **Group Size**: {num_people} people
            **Budget Preference**: {budget}
            **Food Preferences**: {food_preference} (Always include famous local street foods and specialties!)
            {f"**Live Events Happening During Your Trip:** {events_text}" if events_text else ""}

            The itinerary should include:
            - Flight Details ✈️  
                        Arrival and departure times
                        Flight numbers and airlines
                        Duration and layovers
            - Hotel Information 🏨 
                        Check-in and check-out times
                        Hotel name, rating, and location
                        Key amenities
            - Day-by-Day Activities 📅 
                        Morning, afternoon, and evening plans
                        Estimated durations for each activity
                        Flexibility for leisure or optional events
            - Must-Visit Attractions 🏛️ 
                        Top landmarks or experiences
                        Suggested visit times and duration
                        Tips for avoiding crowds or optimizing time
            - Restaurant Recommendations 🍴 
                        Breakfast, lunch, and dinner options
                        Specialty cuisine or local favorites
                        Approximate price range
            - Local Transportation Tips 🚌🚇 
                        Best modes of transport between destinations
                        Estimated travel time
                        Cost-saving or convenient options

             **Itinerary Formatting Guidelines**:
            -Headings: 
                    # for the main itinerary title 
                    ## for each day,
                    ### for sub-sections like Flights, Hotel, Activities
            -Emojis: Use relevant emojis for quick visual cues: 
                    🏛️ Landmarks / attractions
                    🍽️ Restaurants / meals
                    🏨 Hotel stays
                    ✈️ Flights / travel
            -Bullet Points:
                    Use - or * to list activities, restaurants, or attractions
            -Estimated Timings:
                    Include approximate start and end times for activities (e.g., 09:00 AM – 11:00 AM)
            -Visual Appeal:
                    Keep sections clearly separated
                    Use bold for key points (hotel name, flight numbers, restaurant names)
                    Maintain consistent formatting for easy readability
            """,
            agent=analyze_agent,
            expected_output="A comprehensive, Markdown-formatted itinerary including flights, accommodations, and a detailed daily schedule, enhanced with emojis, headers, and bullet points for readability."
        )

        itinerary_planner_crew = Crew(
            agents=[analyze_agent],
            tasks=[analyze_task],
            process=Process.sequential,
            verbose=False
        )

        crew_results = await asyncio.to_thread(itinerary_planner_crew.kickoff)

        if hasattr(crew_results, 'outputs') and crew_results.outputs:
            return crew_results.outputs[0]
        elif hasattr(crew_results, 'get'):
            return crew_results.get("AI Travel Planner", "No itinerary available.")
        else:
            return str(crew_results)

    except Exception as e:
        print(f"DEBUG: Itinerary Error: {e}")
        logger.exception(f"Error generating itinerary: {str(e)}")
        return "Unable to generate itinerary due to an error. Please try again later."


# ===============
#  API Endpoints
# ===============
@app.post("/search_flights/", response_model=AIResponse)
async def get_flight_recommendations(flight_request: FlightRequest):
    """Search flights and get AI recommendation."""
    try:
        flights = await search_flights(flight_request)

        if isinstance(flights, dict) and "error" in flights:
            raise HTTPException(status_code=400, detail=flights["error"])

        if not flights:
            raise HTTPException(status_code=404, detail="No flights found")

        flights_text = format_travel_data("flights", flights)

        ai_recommendation = await get_ai_recommendation("flights", flights_text)

        return AIResponse(
            flights=flights,
            ai_flight_recommendation=ai_recommendation
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Flight search endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Flight search error: {str(e)}")

@app.post("/search_hotels/", response_model=AIResponse)
async def get_hotel_recommendations(hotel_request: HotelRequest):
    """Search hotels and get AI recommendation."""
    try:
        hotels = await search_hotels(hotel_request)

        if isinstance(hotels, dict) and "error" in hotels:
            raise HTTPException(status_code=400, detail=hotels["error"])

        if not hotels:
            raise HTTPException(status_code=404, detail="No hotels found")

        hotels_text = format_travel_data("hotels", hotels)

        ai_recommendation = await get_ai_recommendation("hotels", hotels_text)

        return AIResponse(
            hotels=hotels,
            ai_hotel_recommendation=ai_recommendation
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Hotel search endpoint error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Hotel search error: {str(e)}")


@app.post("/complete_search/", response_model=AIResponse)
async def complete_travel_search(flight_request: FlightRequest, hotel_request: Optional[HotelRequest] = None):
    """Search for flights and hotels concurrently, supports multi-city destinations.
    Each feature is fully fault-isolated: a failure in any one does NOT affect the others.
    """

    # Pre-initialize ALL output variables so a failed feature never causes NameError
    flights           = []
    all_hotel_objects = []
    ai_flight_rec     = ""
    weather_combined  = ""
    ai_weather_rec    = ""
    itinerary         = ""
    map_coords        = []
    expenses          = {}
    culture_guide     = ""
    dest_images       = []
    dest_desc         = ""
    combined_events   = ""

    # 1. Parse destinations (multi-city support)
    try:
        destinations        = [d.strip() for d in flight_request.destination.split(",") if d.strip()]
        primary_destination = destinations[0]
    except Exception as e:
        logger.error(f"Destination parsing failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid destination provided.")

    # 2. Flights — only if travel_mode is flight
    is_flight_trip = flight_request.travel_mode.lower() in ["flight", "fly", "air", "airplane", "plane"]
    if is_flight_trip:
        try:
            flight_result = await get_flight_recommendations(flight_request)
            flights       = flight_result.flights
            ai_flight_rec = flight_result.ai_flight_recommendation
        except Exception as e:
            logger.error(f"[FEATURE FAIL] Flights: {e}")
    else:
        logger.info(f"Skipping flight search — travel mode is '{flight_request.travel_mode}'")
        ai_flight_rec = f"✅ No flights needed — traveling by **{flight_request.travel_mode}**. Plan your road/train route accordingly!"

    flights_text = format_travel_data("flights", flights)

    # 3. Per-city: hotels, weather, images, description, live events
    all_hotels_texts  = []
    all_weather_texts = []
    all_images_list   = []
    all_desc_list     = []
    all_events_list   = []

    for city in destinations:

        # Hotels
        try:
            city_hotel_req = HotelRequest(
                location=city,
                check_in_date=flight_request.outbound_date,
                check_out_date=flight_request.return_date,
                num_people=flight_request.num_people,
                budget=flight_request.budget,
                food_preference=flight_request.food_preference
            )
            h_res = await get_hotel_recommendations(city_hotel_req)
            if hasattr(h_res, "hotels") and h_res.hotels:
                all_hotels_texts.append(f"**Hotels in {city}:**\n{format_travel_data('hotels', h_res.hotels)}")
                all_hotel_objects.extend(h_res.hotels)
        except Exception as e:
            logger.error(f"[FEATURE FAIL] Hotels for {city}: {e}")

        # Weather
        try:
            w = await get_weather(city, flight_request.outbound_date, flight_request.return_date)
            if w:
                all_weather_texts.append(f"**Weather in {city}:**\n{w}")
        except Exception as e:
            logger.error(f"[FEATURE FAIL] Weather for {city}: {e}")

        # Destination Images (Unsplash)
        try:
            imgs = await fetch_destination_images(city)
            all_images_list.extend(imgs)
        except Exception as e:
            logger.error(f"[FEATURE FAIL] Images for {city}: {e}")

        # Description (Wikipedia)
        try:
            desc = await fetch_destination_description(city)
            if desc:
                all_desc_list.append(f"**{city}:** {desc}")
        except Exception as e:
            logger.error(f"[FEATURE FAIL] Description for {city}: {e}")

        # Live Events (Ticketmaster)
        try:
            ev = await fetch_live_events(city, flight_request.outbound_date, flight_request.return_date)
            if ev:
                all_events_list.append(ev)
        except Exception as e:
            logger.error(f"[FEATURE FAIL] Live events for {city}: {e}")

    # Combine per-city results
    hotels_text      = "\n\n".join(all_hotels_texts) if all_hotels_texts else "No hotels found."
    weather_combined = "\n\n".join(all_weather_texts) if all_weather_texts else "Weather data unavailable."
    dest_images      = all_images_list[:3]
    dest_desc        = "\n\n".join(all_desc_list)
    combined_events  = "\n\n".join(all_events_list)

    # 4. AI Weather Recommendation
    try:
        ai_weather_rec = await get_ai_recommendation("weather", weather_combined)
    except Exception as e:
        logger.error(f"[FEATURE FAIL] AI weather recommendation: {e}")

    # 5. Itinerary Generation
    if all_hotel_objects or destinations:
        try:
            itinerary = await generate_itinerary(
                destination=", ".join(destinations),
                flights_text=flights_text if flights else f"Travel by {flight_request.travel_mode}.",
                hotels_text=hotels_text,
                check_in_date=flight_request.outbound_date,
                check_out_date=flight_request.return_date,
                num_people=flight_request.num_people,
                budget=flight_request.budget,
                food_preference=flight_request.food_preference,
                events_text=combined_events
            )
            if not itinerary:
                itinerary = "I apologize, but I encountered an error while generating your itinerary. Please check the hotel and weather recommendations below for inspiration!"
        except Exception as e:
            logger.error(f"[FEATURE FAIL] Itinerary generation: {e}")
            itinerary = f"Error generating itinerary: {str(e)}"

    else:
        logger.warning("Skipping itinerary - no flights or hotels found.")

    # 6. Interactive Map Coordinates
    if itinerary:
        try:
            extracted_places = await extract_locations_from_itinerary(itinerary)
            coord_tasks      = [get_location_coordinates(p, primary_destination) for p in extracted_places]
            coord_results    = await asyncio.gather(*coord_tasks, return_exceptions=True)
            map_coords       = [c for c in coord_results if c is not None and not isinstance(c, Exception)]
        except Exception as e:
            logger.error(f"[FEATURE FAIL] Map coordinates: {e}")

        # 7. Expense Estimator
        try:
            check_in  = datetime.strptime(flight_request.outbound_date, "%Y-%m-%d")
            check_out = datetime.strptime(flight_request.return_date,   "%Y-%m-%d")
            days      = max((check_out - check_in).days, 1)
            expenses  = await estimate_trip_expenses(
                flights_text=flights_text,
                hotels_text=hotels_text,
                itinerary=itinerary,
                num_people=flight_request.num_people,
                days=days,
                budget=flight_request.budget
            )
        except Exception as e:
            logger.error(f"[FEATURE FAIL] Expense estimator: {e}")

        # 8. Culture & Language Guide
        try:
            culture_guide = await generate_culture_guide(", ".join(destinations))
        except Exception as e:
            logger.error(f"[FEATURE FAIL] Culture guide: {e}")

    # Final Response
    return AIResponse(
        flights=flights,
        hotels=all_hotel_objects,
        ai_flight_recommendation=ai_flight_rec,
        ai_hotel_recommendation="",
        weather=weather_combined,
        ai_weather_recommendation=ai_weather_rec,
        itinerary=itinerary,
        map_coordinates=map_coords,
        expenses=expenses,
        culture_guide=culture_guide,
        destination_images=dest_images,
        destination_description=dest_desc,
        live_events=combined_events
    )





@app.post("/parse_intent/")
async def parse_user_intent(request: dict):
    """Use Groq AI to extract trip details from a free-form user message.
    Uses direct Groq API (not CrewAI) for speed and reliability.
    """
    user_message = request.get("message", "")
    if not user_message:
        return {}

    from groq import Groq
    today = datetime.now().strftime("%Y-%m-%d")
    client = Groq(api_key=GROQ_API_KEY)

    system_prompt = f"""You are a travel intent extractor. Extract trip details from user messages and return ONLY a valid JSON object.

Today's date is {today}.

JSON keys to extract:
- "travel_mode": MUST be "flight", "road", "train", or "bus". Infer from words like "road trip", "flying", "by train", "bus journey". Default to "flight" if not mentioned.
- "origin": 3-letter airport code (e.g. "BLR", "SFO") only if user mentions "from [place]".
- "destination": The main city name.
- "start_date": Normalized to YYYY-MM-DD. Handle formats like "04-05-2026", "May 10", "10th of May".
- "num_days": integer.
- "num_people": integer.
- "budget": "Luxury", "Moderate", or "Budget".
- "food_preference": string description.

Return ONLY the JSON object. No other text."""

    try:
        completion = await asyncio.to_thread(
            client.chat.completions.create,
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0,
            max_tokens=300,
            response_format={"type": "json_object"}
        )
        output = completion.choices[0].message.content.strip()
        
        # Robust JSON extraction
        import re
        json_match = re.search(r'\{.*\}', output, re.DOTALL)
        if json_match:
            output = json_match.group(0)
            
        parsed = json.loads(output)
        logger.info(f"Parsed intent: {parsed}")
        return parsed
    except Exception as e:
        logger.error(f"Intent parsing failed: {e}. Output was: {output if 'output' in locals() else 'None'}")
        # Fallback: very basic manual extraction for destination
        if "to" in user_message.lower():
            dest = user_message.lower().split("to")[-1].split("for")[0].split("starting")[0].strip()
            return {"destination": dest.capitalize()}
        return {}


@app.post("/generate_itinerary/", response_model=AIResponse)
async def get_itinerary(itinerary_request: ItineraryRequest):
    """Generate an itinerary based on provided flight and hotel information."""
    try:
        itinerary = await generate_itinerary(
            destination=itinerary_request.destination,
            flights_text=itinerary_request.flights,
            hotels_text=itinerary_request.hotels,
            check_in_date=itinerary_request.check_in_date,
            check_out_date=itinerary_request.check_out_date,
            num_people=itinerary_request.num_people,
            budget=itinerary_request.budget,
            food_preference=itinerary_request.food_preference
        )

        return AIResponse(itinerary=itinerary)
    except Exception as e:
        logger.exception(f"Itinerary generation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Itinerary generation error: {str(e)}")


# ===================
# Run FastAPI Server
# ===================
if __name__ == "__main__":
    logger.info("Starting Travel Planning API server")
    uvicorn.run(app, host="0.0.0.0", port=8000)