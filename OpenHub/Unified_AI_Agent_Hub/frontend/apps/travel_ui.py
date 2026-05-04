import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

API_BASE_URL = "http://localhost:8000/travel"

def parse_date_flexible(date_str):
    if not date_str or str(date_str).lower() in ["null", "none", ""]: return None
    formats = ["%Y-%m-%d", "%d-%m-%Y", "%m-%d-%Y", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"]
    for fmt in formats:
        try: return datetime.strptime(str(date_str).strip(), fmt).strftime("%Y-%m-%d")
        except: continue
    return None

def render_travel_ui():
    st.title("✈️ AI Trip Planner")
    
    # Session State
    for key, default in [("travel_messages", []), ("travel_trip_data", {}), ("travel_search_complete", False), ("travel_initialized", False), ("travel_awaiting_field", None), ("travel_final_data", None)]:
        if key not in st.session_state: st.session_state[key] = default

    FIELD_QUESTIONS = {
        "travel_mode": "How are you planning to travel? ✈️ **Flight**, 🚗 **Road trip**, 🚂 **Train**, or 🚌 **Bus**?",
        "origin": "Which airport are you flying **from**? (3-letter code, e.g. BLR, DEL, BOM)",
        "destination": "Where would you like to go? (city name or multiple cities separated by commas)",
        "start_date": "What is your departure date? (YYYY-MM-DD format, e.g. 2026-06-15)",
        "num_days": "How many days is your trip?",
        "num_people": "How many people are traveling?",
        "budget": "What is your total budget for the trip? (Luxury/Moderate/Budget)",
        "food_preference": "Any food preferences? (e.g. local street food, vegan, fine dining)",
    }

    def is_flight_mode():
        return st.session_state.travel_trip_data.get("travel_mode", "").lower() in ["flight", "fly", "air", "plane"]

    def missing_fields():
        missing = []
        for f in FIELD_QUESTIONS.keys():
            if f == "origin" and not is_flight_mode() and st.session_state.travel_trip_data.get("travel_mode"): continue
            if not st.session_state.travel_trip_data.get(f): missing.append(f)
        return missing

    if not st.session_state.travel_initialized:
        st.session_state.travel_messages.append({"role": "assistant", "content": "👋 Hi! I'm your **AI Travel Planner**. Tell me about your trip in one message!"})
        st.session_state.travel_initialized = True

    # Main Chat Loop
    for msg in st.session_state.travel_messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    if st.session_state.travel_final_data:
        data = st.session_state.travel_final_data
        st.markdown("---")
        
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📅 Itinerary", "🗺️ Map", "🎭 Events & Culture", "🌦️ Weather", "📊 Budget & Gallery"])
        
        with tab1:
            st.markdown(data.get("itinerary", "No itinerary generated."))
            if data.get("ai_flight_recommendation"): st.info(data["ai_flight_recommendation"])
        
        with tab2:
            st.subheader("📍 Interactive Trip Map")
            coords = data.get("map_coordinates", [])
            if coords:
                df_map = pd.DataFrame(coords)
                st.map(df_map)
                for c in coords: st.write(f"- **{c['name']}**")
            else:
                st.info("No map coordinates found for the itinerary.")

        with tab3:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("🎭 Live Events")
                st.markdown(data.get("live_events", "No live events found for these dates."))
            with col2:
                st.subheader("🗣️ Culture & Language")
                st.markdown(data.get("culture_guide", "Culture guide unavailable."))

        with tab4:
            st.subheader("🌦️ Weather Forecast")
            st.markdown(data.get("weather", "Weather data unavailable."))
            if data.get("ai_weather_recommendation"): st.success(data["ai_weather_recommendation"])

        with tab5:
            col1, col2 = st.columns([1, 2])
            with col1:
                st.subheader("💰 Estimated Budget")
                expenses = data.get("expenses", {})
                if expenses:
                    df_exp = pd.DataFrame(list(expenses.items()), columns=["Category", "Cost"])
                    st.plotly_chart(px.pie(df_exp, values="Cost", names="Category", hole=0.3))
                else: st.info("Expense data unavailable.")
            with col2:
                st.subheader("🖼️ Destination Gallery")
                images = data.get("destination_images", [])
                if images: st.image(images, width="stretch")
                st.markdown(f"*{data.get('destination_description', '')}*")

    if prompt := st.chat_input("Type your trip request..."):
        with st.chat_message("user"): st.markdown(prompt)
        st.session_state.travel_messages.append({"role": "user", "content": prompt})

        if st.session_state.travel_awaiting_field:
            field = st.session_state.travel_awaiting_field
            if field == "start_date":
                norm = parse_date_flexible(prompt)
                if norm: st.session_state.travel_trip_data[field] = norm
            elif field in ["num_days", "num_people"]:
                try: st.session_state.travel_trip_data[field] = int(prompt)
                except: pass
            else: st.session_state.travel_trip_data[field] = prompt
            st.session_state.travel_awaiting_field = None
        else:
            with st.spinner("Understanding..."):
                try:
                    res = requests.post(f"{API_BASE_URL}/parse_intent", json={"message": prompt})
                    if res.status_code == 200:
                        parsed = res.json()
                        for k, v in parsed.items():
                            if v and str(v).lower() not in ["null", "none"]:
                                if k == "start_date":
                                    norm = parse_date_flexible(v)
                                    if norm: st.session_state.travel_trip_data[k] = norm
                                else: st.session_state.travel_trip_data[k] = v
                except: pass

        remaining = missing_fields()
        if remaining:
            st.session_state.travel_awaiting_field = remaining[0]
            q = FIELD_QUESTIONS[remaining[0]]
            with st.chat_message("assistant"): st.markdown(q)
            st.session_state.travel_messages.append({"role": "assistant", "content": q})
        else:
            td = st.session_state.travel_trip_data
            with st.spinner("AI is building your perfect trip..."):
                try:
                    # Calculate return date
                    start_dt = datetime.strptime(td["start_date"], "%Y-%m-%d")
                    return_str = (start_dt + timedelta(days=int(td["num_days"]))).strftime("%Y-%m-%d")
                    payload = {
                        "origin": td.get("origin", "XXX"), 
                        "destination": td["destination"],
                        "outbound_date": td["start_date"], 
                        "return_date": return_str,
                        "num_people": td["num_people"], 
                        "num_days": td["num_days"],
                        "budget": td["budget"],
                        "food_preference": td["food_preference"], 
                        "travel_mode": td.get("travel_mode", "flight")
                    }
                    res = requests.post(f"{API_BASE_URL}/complete_search", json=payload, timeout=300)
                    if res.status_code == 200:
                        st.session_state.travel_final_data = res.json()
                        st.success("🎉 Trip Generated! Refreshing view...")
                        st.rerun()
                    else:
                        st.error(f"Failed to generate trip (Error {res.status_code}). Please try again.")
                except Exception as e:
                    st.error(f"Error building trip: {e}")
