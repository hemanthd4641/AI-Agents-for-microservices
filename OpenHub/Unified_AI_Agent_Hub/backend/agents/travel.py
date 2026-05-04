import os
import asyncio
import logging
import requests
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from crewai import Agent, Task, Crew, Process, LLM
from datetime import datetime
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/travel", tags=["Travel"])

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
    return LLM(
        model="groq/llama-3.1-8b-instant",
        api_key=GROQ_API_KEY
    )

# ==========================
#  Pydantic Models
# ==========================
from typing import List, Optional, Union

class TravelRequest(BaseModel):
    origin: str
    destination: str
    outbound_date: str
    return_date: str
    num_people: Union[int, str] = 1
    num_days: Union[int, str] = 1
    budget: str = "Moderate"
    food_preference: str = "Any"
    travel_mode: str = "flight"

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
#  Utility Search Functions
# ==========================

async def run_search(query: str, endpoint: str = "search"):
    url = f"https://google.serper.dev/{endpoint}"
    payload = json.dumps({"q": query})
    headers = {'X-API-KEY': SERP_API_KEY, 'Content-Type': 'application/json'}
    try:
        response = await asyncio.to_thread(requests.post, url, headers=headers, data=payload, timeout=15)
        return response.json()
    except Exception as e:
        logger.error(f"Serper error: {e}")
        return {"error": str(e)}

async def get_weather(city: str, start_date: str, end_date: str) -> str:
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json"
        geo_res = await asyncio.to_thread(requests.get, geo_url, timeout=10)
        geo_data = geo_res.json()
        if not geo_data.get("results"): return f"Weather forecast unavailable for {city}."
        lat, lon = geo_data["results"][0]["latitude"], geo_data["results"][0]["longitude"]
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=auto&start_date={start_date}&end_date={end_date}"
        weather_res = await asyncio.to_thread(requests.get, weather_url)
        data = weather_res.json()
        if "daily" not in data: return "Weather forecast unavailable."
        daily = data["daily"]
        forecast = [f"Daily Weather Forecast for {city}:"]
        for i in range(len(daily["time"])):
            forecast.append(f"- {daily['time'][i]}: High: {daily['temperature_2m_max'][i]}°C | Low: {daily['temperature_2m_min'][i]}°C | Precip: {daily['precipitation_probability_max'][i]}%")
        return "\n".join(forecast)
    except: return "Weather forecast unavailable."

async def fetch_destination_images(city: str) -> List[str]:
    try:
        url = "https://google.serper.dev/images"
        payload = json.dumps({"q": f"{city} landmarks travel", "num": 5})
        headers = {'X-API-KEY': SERP_API_KEY, 'Content-Type': 'application/json'}
        response = await asyncio.to_thread(requests.post, url, headers=headers, data=payload, timeout=10)
        data = response.json()
        return [img["imageUrl"] for img in data.get("images", []) if "imageUrl" in img]
    except: return []

async def fetch_destination_description(city: str) -> str:
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{city.replace(' ', '_')}"
        res = await asyncio.to_thread(requests.get, url, timeout=10)
        if res.status_code == 200: return res.json().get("extract", "")
    except: pass
    return f"Explore {city}!"

async def fetch_live_events(city: str, start_date: str, end_date: str) -> str:
    if not TICKETMASTER_API_KEY: return ""
    try:
        url = "https://app.ticketmaster.com/discovery/v2/events.json"
        params = {"apikey": TICKETMASTER_API_KEY, "city": city, "startDateTime": f"{start_date}T00:00:00Z", "endDateTime": f"{end_date}T23:59:59Z", "size": 5}
        res = await asyncio.to_thread(requests.get, url, params=params)
        data = res.json()
        events = data.get("_embedded", {}).get("events", [])
        if not events: return ""
        lines = [f"🎭 **Live Events in {city}:**"]
        for e in events: lines.append(f"- {e.get('name')} | {e.get('dates', {}).get('start', {}).get('localDate', 'TBD')}")
        return "\n".join(lines)
    except: return ""

async def get_location_coordinates(place_name: str, city: str):
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={place_name} {city}&count=1&language=en&format=json"
        geo_res = await asyncio.to_thread(requests.get, geo_url)
        data = geo_res.json()
        if data.get("results"):
            return MapCoordinate(name=place_name, lat=data["results"][0]["latitude"], lon=data["results"][0]["longitude"])
    except: return None

# ==========================
#  AI Formatting & Agents
# ==========================

def format_travel_data(data_type, data):
    if not data: return f"No {data_type} available."
    if data_type == "flights":
        text = "**Available flight options**:\n\n"
        for i, f in enumerate(data):
            text += f"**Flight {i+1}:** {f.airline} | {f.price} | {f.duration} | {f.departure} to {f.arrival}\n"
    elif data_type == "hotels":
        text = "**Available Hotel Options**:\n\n"
        for i, h in enumerate(data):
            text += f"**Hotel {i+1}:** {h.name} | Rating: {h.rating} | Loc: {h.location}\n"
    return text

async def get_ai_recommendation(data_type, formatted_data):
    llm = initialize_llm()
    agent = Agent(role=f"AI {data_type.capitalize()} Analyst", goal=f"Recommend the best {data_type}.", backstory=f"Expert in {data_type} analysis.", llm=llm, verbose=True)
    task = Task(description=f"Analyze these {data_type} and recommend the best one:\n{formatted_data}", agent=agent, expected_output=f"Concise {data_type} recommendation")
    crew = Crew(agents=[agent], tasks=[task], max_rpm=1)
    results = await asyncio.to_thread(crew.kickoff)
    return str(results.raw) if hasattr(results, 'raw') else str(results)

async def generate_itinerary(destination, flights_text, hotels_text, check_in_date, check_out_date, num_people, budget, food_preference, events_text=""):
    llm = initialize_llm()
    agent = Agent(role="Senior Travel Architect", goal=f"Generate a full itinerary for {destination}.", backstory="Master of detailed travel planning.", llm=llm, verbose=True)
    task = Task(description=f"Create a detailed day-by-day itinerary for {destination} from {check_in_date} to {check_out_date}. Include flights, hotels, food, and local events.\nFlights: {flights_text}\nHotels: {hotels_text}\nEvents: {events_text}\nBudget: {budget}, Food: {food_preference}.", agent=agent, expected_output="Markdown Itinerary")
    crew = Crew(agents=[agent], tasks=[task], max_rpm=1)
    results = await asyncio.to_thread(crew.kickoff)
    return str(results.raw) if hasattr(results, 'raw') else str(results)

async def estimate_trip_expenses(flights_text, hotels_text, itinerary, num_people, days, budget):
    llm = initialize_llm()
    agent = Agent(role="Financial Analyst", goal="Estimate total trip cost in USD.", backstory="Expert in travel budgeting.", llm=llm, verbose=True)
    task = Task(description=f"Return a JSON object with keys: Flights, Accommodation, Food, Activities. Group Size: {num_people}, Days: {days}, Budget: {budget}.", agent=agent, expected_output="Valid JSON")
    crew = Crew(agents=[agent], tasks=[task], max_rpm=1)
    results = await asyncio.to_thread(crew.kickoff)
    output = str(results.raw) if hasattr(results, 'raw') else str(results)
    try:
        output = output.replace('```json', '').replace('```', '').strip()
        start, end = output.find('{'), output.rfind('}') + 1
        return json.loads(output[start:end])
    except: return {"Flights": 0, "Accommodation": 0, "Food": 0, "Activities": 0}

async def generate_culture_guide(destination):
    llm = initialize_llm()
    agent = Agent(role="Local Culture Expert", goal=f"Survival guide for {destination}.", backstory="Expert in local customs.", llm=llm, verbose=True)
    task = Task(description=f"Create a guide for {destination} with phrases and etiquette.", agent=agent, expected_output="Markdown Guide")
    crew = Crew(agents=[agent], tasks=[task], max_rpm=1)
    results = await asyncio.to_thread(crew.kickoff)
    return str(results.raw) if hasattr(results, 'raw') else str(results)

# ==========================
#  Core API Endpoints
# ==========================

@router.post("/search_flights", response_model=AIResponse)
async def get_flight_recommendations(request: TravelRequest):
    query = f"flights from {request.origin} to {request.destination} on {request.outbound_date} return {request.return_date}"
    res = await run_search(query)
    organic = res.get("organic", [])
    flights = [FlightInfo(airline=r.get("title", "Flight"), price="Check site", duration="Check site", stops="Check site", departure=request.outbound_date, arrival=request.destination, travel_class="Economy", return_date=request.return_date, airline_logo="") for r in organic[:3]]
    return AIResponse(flights=flights, ai_flight_recommendation=await get_ai_recommendation("flights", format_travel_data("flights", flights)))

@router.post("/search_hotels", response_model=AIResponse)
async def get_hotel_recommendations(request: TravelRequest, city: str = None):
    search_city = city if city else request.destination.split(",")[0].strip()
    query = f"hotels in {search_city} check-in {request.outbound_date} check-out {request.return_date}"
    res = await run_search(query, endpoint="places")
    places = res.get("places", [])
    hotels = [HotelInfo(name=h.get("title", "Hotel"), price="Check site", rating=float(h.get("rating", 0.0)), location=h.get("address", "N/A"), link=f"https://www.google.com/search?q={h.get('title')}") for h in places[:5]]
    return AIResponse(hotels=hotels, ai_hotel_recommendation=await get_ai_recommendation("hotels", format_travel_data("hotels", hotels)))

@router.post("/complete_search", response_model=AIResponse)
async def complete_travel_search(request: TravelRequest):
    print(f"📥 Received Travel Request Payload: {request.model_dump()}")
    try:
        request.num_people = int(request.num_people)
        request.num_days = int(request.num_days)
    except: pass
    
    destinations = [d.strip() for d in request.destination.split(",") if d.strip()]
    primary_city = destinations[0]
    
    flights, ai_flight_rec = [], ""
    if request.travel_mode.lower() in ["flight", "fly", "air", "plane"]:
        f_res = await get_flight_recommendations(request)
        flights, ai_flight_rec = f_res.flights, f_res.ai_flight_recommendation
    else:
        ai_flight_rec = f"Traveling by {request.travel_mode}."

    all_hotels, all_weather, all_images, all_desc, all_events = [], [], [], [], []
    for city in destinations:
        try:
            h_res = await get_hotel_recommendations(request, city)
            all_hotels.extend(h_res.hotels)
            all_weather.append(await get_weather(city, request.outbound_date, request.return_date))
            all_images.extend(await fetch_destination_images(city))
            all_desc.append(await fetch_destination_description(city))
            all_events.append(await fetch_live_events(city, request.outbound_date, request.return_date))
        except Exception as e:
            logger.error(f"Error in city loop: {e}")

    weather_text = "\n\n".join(all_weather)
    itinerary = await generate_itinerary(", ".join(destinations), format_travel_data("flights", flights), format_travel_data("hotels", all_hotels), request.outbound_date, request.return_date, request.num_people, request.budget, request.food_preference, "\n\n".join(all_events))
    
    try:
        check_in = datetime.strptime(request.outbound_date, "%Y-%m-%d")
        check_out = datetime.strptime(request.return_date, "%Y-%m-%d")
        days = max((check_out - check_in).days, 1)
    except: days = 1
    
    expenses = await estimate_trip_expenses(format_travel_data("flights", flights), format_travel_data("hotels", all_hotels), itinerary, request.num_people, days, request.budget)
    
    return AIResponse(
        flights=flights, hotels=all_hotels, ai_flight_recommendation=ai_flight_rec,
        weather=weather_text, ai_weather_recommendation=await get_ai_recommendation("weather", weather_text),
        itinerary=itinerary, map_coordinates=[], expenses=expenses,
        culture_guide=await generate_culture_guide(primary_city),
        destination_images=all_images[:5], destination_description="\n\n".join(all_desc),
        live_events="\n\n".join(all_events)
    )

@router.post("/parse_intent")
async def parse_intent(request: dict):
    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)
    today = datetime.now().strftime("%Y-%m-%d")
    prompt = f"Today: {today}. Extract travel details to JSON: travel_mode, origin, destination, start_date, num_days, num_people, budget, food_preference."
    try:
        comp = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": f"{prompt}\nMsg: {request.get('message')}"}], response_format={"type": "json_object"})
        return json.loads(comp.choices[0].message.content)
    except: return {}
