import streamlit as st
import requests
import time
from fpdf import FPDF
import io

# Page Config
st.set_page_config(page_title="AI Fitness Coach", page_icon="💪", layout="centered")

# Styling
st.markdown("""
    <style>
    .stChatMessage { border-radius: 15px; }
    .stButton>button { width: 100%; border-radius: 20px; }
    </style>
    """, unsafe_allow_html=True)

# Session State for Conversation
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "👋 Hello! I'm your AI Fitness Coach. I'll help you build a custom workout and meal plan. First, tell me your **Age**?"}
    ]
if "step" not in st.session_state:
    st.session_state.step = 0
if "user_data" not in st.session_state:
    st.session_state.user_data = {}

# Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Sequential Questions
questions = [
    "Great! What is your current **Weight** (e.g., 75kg)?",
    "And your **Height** (e.g., 180cm)?",
    "What is your primary **Goal**? (Weight Loss, Muscle Gain, Endurance, etc.)",
    "What **Equipment** do you have access to? (Gym, Dumbbells only, or No equipment?)",
    "Last one: Any **Dietary Preferences**? (None, Vegan, Keto, High Protein, etc.)"
]

keys = ["age", "weight", "height", "goal", "equipment", "diet_pref"]

# Input Logic
if st.session_state.step < len(keys):
    if prompt := st.chat_input("Type your answer here..."):
        # Store user answer
        st.session_state.user_data[keys[st.session_state.step]] = prompt
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Move to next question or start generation
        st.session_state.step += 1
        
        if st.session_state.step < len(keys):
            next_q = questions[st.session_state.step - 1]
            st.session_state.messages.append({"role": "assistant", "content": next_q})
        else:
            st.session_state.messages.append({"role": "assistant", "content": "✅ Got everything! I'm now crafting your personalized transformation plan. This will take about 30-60 seconds... 🏋️‍♂️🥗"})
        
        st.rerun()

# Generation Trigger
if st.session_state.step == len(keys) and "final_result" not in st.session_state:
    with st.spinner("Crunching data and designing your plan..."):
        try:
            response = requests.post("http://localhost:8003/generate_plan", json=st.session_state.user_data, timeout=300)
            if response.status_code == 200:
                st.session_state.final_result = response.json()["final_plan"]
                st.session_state.messages.append({"role": "assistant", "content": "✨ **Your Plan is Ready!** Check it out below:"})
                st.rerun()
            else:
                st.error("Trainer is busy. Please try again later.")
        except Exception as e:
            st.error(f"Connection failed: {e}")

# Show Final Result
if "final_result" in st.session_state:
    st.markdown("---")
    st.markdown(st.session_state.final_result)
    
    # PDF Generation Function
    def generate_pdf(content):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "Your AI Fitness Plan", ln=True, align='C')
        pdf.ln(10)
        pdf.set_font("Arial", size=12)
        
        # Simple markdown-to-pdf logic
        for line in content.split('\n'):
            # Replace common markdown symbols for better PDF look
            clean_line = line.replace('**', '').replace('###', '').replace('##', '').replace('#', '')
            # Handle unicode/emojis by replacing with '?' for simple Arial
            pdf.multi_cell(0, 10, txt=clean_line.encode('latin-1', 'replace').decode('latin-1'))
        
        return pdf.output(dest='S')

    pdf_bytes = generate_pdf(st.session_state.final_result)
    
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="📥 Download PDF",
            data=pdf_bytes,
            file_name="My_Fitness_Plan.pdf",
            mime="application/pdf"
        )
    with col2:
        st.download_button(
            label="📄 Download Markdown",
            data=st.session_state.final_result,
            file_name="My_Fitness_Plan.md",
            mime="text/markdown"
        )
    
    if st.button("🔄 Start Over"):
        st.session_state.clear()
        st.rerun()
