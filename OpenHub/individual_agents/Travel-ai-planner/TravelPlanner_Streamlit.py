import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

API_BASE_URL = "http://localhost:8000"
API_URL_COMPLETE = f"{API_BASE_URL}/complete_search/"
API_URL_PARSE    = f"{API_BASE_URL}/parse_intent/"

st.set_page_config(page_title="AI Travel Planner", page_icon="✈️", layout="centered")

st.title("✈️ AI Trip Planner")
st.caption("Tell me about your trip in one message, or answer my questions step by step!")

# ── Session State ─────────────────────────────────────────────────────────────
for key, default in [
    ("messages", []),
    ("trip_data", {}),
    ("search_complete", False),
    ("initialized", False),
    ("awaiting_field", None),   # which specific field we just asked for
    ("initial_parsed", False),  # whether we already ran the AI parser
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Field metadata ─────────────────────────────────────────────────────────────
FIELD_QUESTIONS = {
    "travel_mode":     "How are you planning to travel? ✈️ **Flight**, 🚗 **Road trip**, 🚂 **Train**, or 🚌 **Bus**?",
    "origin":          "Which airport are you flying **from**? (3-letter code, e.g. BLR, DEL, BOM)",
    "destination":     "Where would you like to go? (city name or multiple cities separated by commas)",
    "start_date":      "What is your departure date? (YYYY-MM-DD format, e.g. 2026-06-15)",
    "num_days":        "How many days is your trip?",
    "num_people":      "How many people are traveling?",
    "budget":          "What is your total budget for the trip? (e.g. 5000 USD, 10k, or Luxury/Budget)",
    "food_preference": "Any food preferences? (e.g. local street food, vegan, fine dining)",
}
ALL_FIELDS = list(FIELD_QUESTIONS.keys())

def parse_date_flexible(date_str):
    """Try multiple date formats and return YYYY-MM-DD string."""
    if not date_str or str(date_str).lower() in ["null", "none", ""]:
        return None
    
    formats = [
        "%Y-%m-%d", "%d-%m-%Y", "%m-%d-%Y",
        "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d",
        "%d-%m-%y", "%m-%d-%y",
        "%d %B %Y", "%B %d %Y", "%d %b %Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(str(date_str).strip(), fmt).strftime("%Y-%m-%d")
        except:
            continue
    # Try dateutil as last resort
    try:
        from dateutil import parser as dateutil_parser
        return dateutil_parser.parse(str(date_str), dayfirst=True).strftime("%Y-%m-%d")
    except:
        return None

def is_flight_mode():
    mode = st.session_state.trip_data.get("travel_mode", "").lower()
    return mode in ["flight", "fly", "air", "airplane", "plane", "yes"]

def add_message(role, content):
    st.session_state.messages.append({"role": role, "content": content})

def missing_fields():
    missing = []
    for f in ALL_FIELDS:
        # Skip 'origin' if user is not flying
        if f == "origin" and not is_flight_mode():
            # Only skip after travel_mode is already set
            if st.session_state.trip_data.get("travel_mode"):
                continue
        if not st.session_state.trip_data.get(f):
            missing.append(f)
    return missing

def next_question():
    missing = missing_fields()
    if missing:
        return missing[0], FIELD_QUESTIONS[missing[0]]
    return None, None

def parse_and_store(parsed: dict):
    """Store all non-null fields extracted by the AI."""
    mapping = {
        "travel_mode":     "travel_mode",
        "origin":          "origin",
        "destination":     "destination",
        "start_date":      "start_date",
        "num_days":        "num_days",
        "num_people":      "num_people",
        "budget":          "budget",
        "food_preference": "food_preference",
    }
    for key, store_key in mapping.items():
        val = parsed.get(key)
        if val is not None and str(val).strip().lower() not in ["null", "none", ""]:
            if store_key == "start_date":
                normalized = parse_date_flexible(val)
                if normalized:
                    st.session_state.trip_data[store_key] = normalized
            elif store_key in ["num_days", "num_people"]:
                try:
                    st.session_state.trip_data[store_key] = int(val)
                except:
                    pass
            elif store_key == "origin":
                st.session_state.trip_data[store_key] = str(val).strip().upper()
            else:
                st.session_state.trip_data[store_key] = str(val).strip()

# ── Initial greeting ───────────────────────────────────────────────────────────
if not st.session_state.initialized:
    add_message("assistant",
        "👋 Hi! I'm your **AI Travel Planner**.\n\n"
        "Tell me about your trip in one message! For example:\n"
        "> *\"I want to plan a road trip to Chikkamagalur for 4 days starting 2026-05-10, 2 people, budget 5k, local food\"*\n\n"
        "I'll extract the details and only ask for what's missing."
    )
    st.session_state.initialized = True

# ── Sidebar Progress ─────────────────────────────────────────────────────────
with st.sidebar:
    st.header("📍 Trip Progress")
    td = st.session_state.trip_data
    for field, label in [
        ("travel_mode", "Travel Mode"),
        ("destination", "Destination"),
        ("start_date", "Start Date"),
        ("num_days", "Duration"),
        ("num_people", "People"),
        ("budget", "Budget"),
        ("food_preference", "Food"),
        ("origin", "Origin Airport")
    ]:
        val = td.get(field)
        if val:
            st.write(f"✅ **{label}**: {val}")
        else:
            # Only show origin if flying
            if field == "origin" and not is_flight_mode() and td.get("travel_mode"):
                continue
            st.write(f"⚪ *{label}: Pending*")

# ── Display chat history ───────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Input handling ─────────────────────────────────────────────────────────────
if prompt := st.chat_input("Type your trip request or answer here..."):
    if st.session_state.search_complete:
        st.warning("Your trip is planned! Refresh the page to plan another one.")
        st.stop()

    with st.chat_message("user"):
        st.markdown(prompt)
    add_message("user", prompt)

    # ── CASE 1: Bot asked a specific follow-up question — store directly ──────
    if st.session_state.awaiting_field:
        field = st.session_state.awaiting_field
        val = prompt.strip()
        if field == "start_date":
            normalized = parse_date_flexible(val)
            if normalized:
                st.session_state.trip_data[field] = normalized
            else:
                with st.chat_message("assistant"):
                    st.markdown(f"❌ I couldn't understand the date `{val}`. Please enter it as **YYYY-MM-DD** (e.g. `2026-05-10`).")
                add_message("assistant", f"❌ Invalid date format. Please use YYYY-MM-DD.")
                st.stop()
        elif field in ["num_days", "num_people"]:
            try:
                st.session_state.trip_data[field] = int(val)
            except:
                with st.chat_message("assistant"):
                    st.markdown(f"Please enter a valid number.")
                add_message("assistant", "Please enter a valid number.")
                st.stop()
        elif field == "origin":
            st.session_state.trip_data[field] = val.upper()
        else:
            st.session_state.trip_data[field] = val
        st.session_state.awaiting_field = None

    # ── CASE 2: First/free-form message — try AI intent extraction ────────────
    else:
        with st.spinner("Understanding your request..."):
            try:
                parse_resp = requests.post(API_URL_PARSE, json={"message": prompt}, timeout=30)
                if parse_resp.status_code == 200:
                    parsed = parse_resp.json()
                    if parsed:
                        parse_and_store(parsed)
                        # Show what we found
                        found = [k for k, v in st.session_state.trip_data.items() if v]
                        if found:
                            st.toast(f"✅ Extracted: {', '.join(found)}", icon="🎯")
            except Exception as e:
                # Fallback to manual entry for first field if extraction fails
                first_missing = missing_fields()
                if first_missing:
                    field = first_missing[0]
                    st.session_state.trip_data[field] = prompt.strip()
        st.session_state.initial_parsed = True

    # ── Ask for any missing fields ─────────────────────────────────────────────
    remaining = missing_fields()

    if remaining:
        next_field = remaining[0]
        question = FIELD_QUESTIONS[next_field]
        filled = len(ALL_FIELDS) - len(remaining)
        response = f"{question}\n\n*(Got {filled}/{len(ALL_FIELDS)} details)*"
        with st.chat_message("assistant"):
            st.markdown(response)
        add_message("assistant", response)
        # Tell the next run exactly which field we're expecting
        st.session_state.awaiting_field = next_field

    else:
        # ── All fields collected — build and fire the API request ─────────────
        td = st.session_state.trip_data

        # Final validation and return date calculation
        try:
            start_dt   = datetime.strptime(td["start_date"], "%Y-%m-%d")
            return_dt  = start_dt + timedelta(days=int(td["num_days"]))
            return_str = return_dt.strftime("%Y-%m-%d")
        except Exception as e:
            with st.chat_message("assistant"):
                st.markdown(f"❌ Date error. Please use YYYY-MM-DD format for your departure date.")
            add_message("assistant", f"❌ Date error. Please use YYYY-MM-DD.")
            st.session_state.trip_data.pop("start_date", None)
            st.session_state.awaiting_field = "start_date"
            st.stop()

            with st.chat_message("assistant"):
                st.markdown(f"❌ Could not parse the date `{td.get('start_date')}`. Please use YYYY-MM-DD format.")
            add_message("assistant", f"❌ Invalid date. Please use YYYY-MM-DD format.")
            st.session_state.trip_data.pop("start_date", None)
            st.stop()

        confirm_msg = (
            f"✅ **Got everything! Here's your trip summary:**\n\n"
            f"- 🛫 **From**: {td.get('origin', 'Not specified')}\n"
            f"- 📍 **To**: {td['destination']}\n"
            f"- 📅 **Dates**: {td['start_date']} → {return_str} ({td['num_days']} days)\n"
            f"- 👥 **People**: {td['num_people']}\n"
            f"- 💰 **Budget**: {td['budget']}\n"
            f"- 🍽️ **Food**: {td['food_preference']}\n\n"
            f"🔍 Searching flights, hotels, weather, events and generating your itinerary..."
        )
        with st.chat_message("assistant"):
            st.markdown(confirm_msg)
        add_message("assistant", confirm_msg)

        st.session_state.search_complete = True

        payload = {
            "flight_request": {
                "origin":          td.get("origin", "XXX"),
                "destination":     td["destination"],
                "outbound_date":   td["start_date"],
                "return_date":     return_str,
                "num_people":      int(td["num_people"]),
                "budget":          td["budget"],
                "food_preference": td["food_preference"],
                "travel_mode":     td.get("travel_mode", "flight")
            }
        }

        with st.spinner("AI is building your perfect trip... this may take a minute ⏳"):
            try:
                response = requests.post(API_URL_COMPLETE, json=payload, timeout=300)
                if response.status_code == 200:
                    result = response.json()

                    # --- ACCUMULATE REPORT FOR PDF ---
                    full_report = f"# TRIP ITINERARY: {td['destination'].upper()}\n\n"
                    full_report += f"**Dates:** {td['start_date']} to {return_str}\n"
                    full_report += f"**People:** {td['num_people']} | **Budget:** {td['budget']}\n\n"
                    full_report += "---\n\n"

                    # 0. Destination Images & Description
                    dest_images = result.get("destination_images", [])
                    dest_desc   = result.get("destination_description", "")
                    if dest_images or dest_desc:
                        with st.chat_message("assistant"):
                            if dest_images:
                                st.image(dest_images[0], use_container_width=True,
                                         caption=f"Welcome to {td['destination']}!")
                            if dest_desc:
                                st.markdown(f"**About {td['destination']}:** {dest_desc}")
                                full_report += f"## About {td['destination']}\n{dest_desc}\n\n"

                    # 1. Weather
                    if result.get("weather"):
                        with st.chat_message("assistant"):
                            st.markdown("### 🌤️ Weather Forecast")
                            st.markdown(result["weather"])
                            full_report += f"## Weather Forecast\n{result['weather']}\n\n"
                            if result.get("ai_weather_recommendation"):
                                st.markdown("#### 🎒 AI Packing Guide")
                                st.markdown(result["ai_weather_recommendation"])
                                full_report += f"### Packing Guide\n{result['ai_weather_recommendation']}\n\n"

                    # 2. Flights
                    if result.get("flights"):
                        with st.chat_message("assistant"):
                            st.markdown("### ✈️ Top Flight Options")
                            flight_text = ""
                            for f in result["flights"][:3]:
                                line = f"**{f['airline']}** | {f['duration']} | {f['stops']} | **₹{f['price']}**"
                                st.markdown(line)
                                flight_text += f"- {line}\n"
                            full_report += f"## Flight Options\n{flight_text}\n\n"
                            if result.get("ai_flight_recommendation"):
                                st.info(result["ai_flight_recommendation"])
                                full_report += f"{result['ai_flight_recommendation']}\n\n"

                    # 3. Hotels
                    if result.get("hotels"):
                        with st.chat_message("assistant"):
                            st.markdown("### 🏨 Recommended Hotels")
                            hotel_text = ""
                            for h in result["hotels"][:3]:
                                line = f"**{h['name']}** | ⭐ {h['rating']} | **₹{h['price']}**/night"
                                st.markdown(line)
                                hotel_text += f"- {line}\n"
                            full_report += f"## Recommended Hotels\n{hotel_text}\n\n"

                    # 4. Itinerary
                    if result.get("itinerary"):
                        with st.chat_message("assistant"):
                            st.markdown("### 📅 Your Personalized Day-by-Day Itinerary")
                            st.markdown(result["itinerary"])
                            full_report += f"## Daily Itinerary\n{result['itinerary']}\n\n"

                    # 5. Interactive Map
                    if result.get("map_coordinates"):
                        with st.chat_message("assistant"):
                            st.markdown("### 🗺️ Interactive Itinerary Map")
                            df = pd.DataFrame(result["map_coordinates"])
                            if not df.empty and "lat" in df.columns and "lon" in df.columns:
                                st.map(df)
                                full_report += "## Map Locations\nIncluded in interactive dashboard.\n\n"

                    # 6. Expense Chart
                    if result.get("expenses"):
                        with st.chat_message("assistant"):
                            st.markdown("### 💰 Estimated Trip Budget (USD)")
                            try:
                                df_exp = pd.DataFrame(list(result["expenses"].items()),
                                                      columns=["Category", "Cost"])
                                fig = px.pie(df_exp, values="Cost", names="Category", hole=0.4,
                                             color_discrete_sequence=px.colors.sequential.Teal)
                                fig.update_traces(textposition="inside", textinfo="percent+label")
                                st.plotly_chart(fig, use_container_width=True)
                                exp_text = "\n".join([f"- {k}: ${v}" for k,v in result['expenses'].items()])
                                full_report += f"## Estimated Expenses\n{exp_text}\n\n"
                            except:
                                st.info("Could not render budget chart.")

                    # 7. Live Events
                    if result.get("live_events"):
                        with st.chat_message("assistant"):
                            st.markdown("### 🎭 Live Events During Your Trip")
                            st.markdown(result["live_events"])
                            full_report += f"## Live Events\n{result['live_events']}\n\n"

                    # 8. Culture Guide
                    if result.get("culture_guide"):
                        with st.chat_message("assistant"):
                            st.markdown("### 🗣️ Local Survival Guide")
                            st.markdown(result["culture_guide"])

                    with st.chat_message("assistant"):
                        st.success("🎉 Your trip is fully planned! Have an amazing journey! ✈️🌍")
                        
                        # --- PDF GENERATION ---
                        try:
                            from fpdf import FPDF
                            
                            class TravelPDF(FPDF):
                                def header(self):
                                    if hasattr(self, 'title_text'):
                                        self.set_font('Arial', 'B', 16)
                                        self.cell(0, 10, self.title_text, 0, 1, 'C')
                                        self.ln(10)
                            
                            pdf = TravelPDF()
                            pdf.title_text = f"Itinerary: {td['destination']}"
                            pdf.add_page()
                            pdf.set_font("Arial", size=12)
                            
                            # Simple cleanup for FPDF (doesn't like emojis or some unicode)
                            def clean_for_pdf(text):
                                # Replace common emojis/symbols with text or nothing
                                replacements = {
                                    '✈️': ' (Flight) ', '🏨': ' (Hotel) ', '📅': ' Day: ', '🍴': ' Food: ',
                                    '💰': ' Budget: ', '🌤️': ' Weather: ', '📍': ' Loc: ', '🎭': ' Event: ',
                                    '🏛️': ' Site: ', '🗣️': ' Info: ', '🎒': ' Tip: ', '🗺️': ' Map: ',
                                    '✅': '[OK]', '❌': '[X]', '🎉': '!!!', '🌍': '', '🛫': 'From: ', '🍴': 'Food: '
                                }
                                for k, v in replacements.items():
                                    text = text.replace(k, v)
                                # Encode to latin-1 and ignore errors to avoid PDF crashes
                                return text.encode('latin-1', 'ignore').decode('latin-1')

                            pdf.multi_cell(0, 10, txt=clean_for_pdf(full_report))
                            pdf_bytes = pdf.output(dest='S')
                            
                            st.download_button(
                                label="📥 Download Trip Itinerary (PDF)",
                                data=pdf_bytes,
                                file_name=f"Trip_to_{td['destination'].replace(' ','_')}.pdf",
                                mime="application/pdf",
                                key="pdf_download"
                            )
                        except Exception as pdf_err:
                            logger.error(f"PDF Error: {pdf_err}")
                            st.info("Note: PDF generation failed, downloading as text instead.")
                            st.download_button(
                                label="📥 Download Trip Itinerary (Text)",
                                data=full_report,
                                file_name=f"Trip_to_{td['destination'].replace(' ','_')}.md",
                                mime="text/markdown",
                                key="md_download"
                            )


                else:
                    st.error(f"Backend error: {response.text}")
            except Exception as e:
                st.error(f"Error connecting to backend: {e}")

# ── Debug ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    with st.expander("🛠️ Debug Information"):
        st.write("**Current Trip Data:**")
        st.json(st.session_state.trip_data)
        st.write(f"**Awaiting Field:** {st.session_state.awaiting_field}")
        st.write(f"**Initial Parsed:** {st.session_state.initial_parsed}")
