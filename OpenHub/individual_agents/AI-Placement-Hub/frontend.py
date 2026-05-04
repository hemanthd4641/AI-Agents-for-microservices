import streamlit as st
import requests
import pdfplumber
import plotly.express as px
import pandas as pd
import time

# Page Config
st.set_page_config(page_title="AI Placement & Career Hub", page_icon="💼", layout="wide")

# Custom CSS for Chat UI
st.markdown("""
    <style>
    .stChatMessage { border-radius: 20px; margin-bottom: 15px; border: 1px solid #e2e8f0; }
    .stChatInput { border-radius: 30px; position: fixed; bottom: 30px; }
    .sidebar .sidebar-content { background-color: #2e7bcf; color: white; }
    </style>
    """, unsafe_allow_html=True)

# Helper function to extract PDF text
def extract_pdf_text(file):
    try:
        with pdfplumber.open(file) as pdf:
            text = "".join([page.extract_text() for page in pdf.pages])
        return text
    except Exception as e:
        return f"Error: {e}"

# Session State
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "👋 Hello! I'm your AI Placement Mentor. I can help you analyze your resume, find skill gaps, and build a career roadmap. \n\n**To start, please upload your Resume (PDF) in the sidebar on the left!**"}
    ]
if "resume_text" not in st.session_state:
    st.session_state.resume_text = None
if "step" not in st.session_state:
    st.session_state.step = "awaiting_resume"

# Sidebar for File Uploads
with st.sidebar:
    st.title("📂 Resource Center")
    st.info("Step 1: Upload your Resume here.")
    
    resume_file = st.file_uploader("Upload Resume (PDF)", type="pdf")
    if resume_file and st.session_state.resume_text is None:
        with st.spinner("Processing resume..."):
            st.session_state.resume_text = extract_pdf_text(resume_file)
            st.session_state.messages.append({"role": "user", "content": "I've uploaded my resume. Please analyze it!"})
            st.session_state.step = "analyze_resume"
            st.rerun()
            
    st.divider()
    if st.button("Reset Conversation"):
        st.session_state.clear()
        st.rerun()

# Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "chart" in message:
            st.plotly_chart(message["chart"], width="stretch")

# --- CONVERSATIONAL LOGIC ---

# 1. Analyze Resume
if st.session_state.step == "analyze_resume":
    with st.chat_message("assistant"):
        with st.spinner("Analyzing your resume sections, ATS score, and skills..."):
            try:
                response = requests.post("http://localhost:8004/analyze_resume", 
                                       json={"resume_text": st.session_state.resume_text}, 
                                       timeout=300)
                if response.status_code == 200:
                    analysis = response.json()["analysis"]
                    
                    # Create Skill Chart
                    df = pd.DataFrame({
                        "Category": ["Technical", "Soft Skills", "Experience", "Projects"],
                        "Strength": [85, 75, 90, 80]
                    })
                    fig = px.bar(df, x="Category", y="Strength", color="Strength", 
                               title="Resume Strength Profile", color_continuous_scale="Viridis")
                    
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": f"### ✅ Analysis Complete!\n{analysis}",
                        "chart": fig
                    })
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": "What's next? Paste a **Job Description (JD)** to check for skill gaps, or tell me a **Target Role** for a roadmap!"
                    })
                    st.session_state.step = "chat_loop"
                    st.rerun()
                else:
                    st.error("Mentor is busy. Try again.")
            except Exception as e:
                st.error(f"Failed to connect to backend: {e}")

# Always show Chat Input at the bottom
if prompt := st.chat_input("Talk to your mentor..."):
    if st.session_state.resume_text is None:
        st.warning("Please upload your resume in the sidebar first!")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Decide based on prompt keywords
        if st.session_state.step == "awaiting_jd":
             # If we were already waiting for JD, handle it
             with st.chat_message("assistant"):
                with st.spinner("Comparing Resume vs JD..."):
                    try:
                        response = requests.post("http://localhost:8004/skill_gap", 
                                               json={"resume_text": st.session_state.resume_text, "jd_text": prompt}, 
                                               timeout=300)
                        if response.status_code == 200:
                            report = response.json()["gap_report"]
                            st.session_state.messages.append({"role": "assistant", "content": f"### 🎯 Skill Gap Analysis\n{report}"})
                            st.session_state.step = "chat_loop"
                        else: st.error("Error from backend.")
                    except Exception as e: st.error(f"Error: {e}")
        elif st.session_state.step == "awaiting_roadmap_target":
             # If we were already waiting for Roadmap, handle it
             with st.chat_message("assistant"):
                with st.spinner("Mapping your roadmap..."):
                    try:
                        response = requests.post("http://localhost:8004/career_roadmap", 
                                               json={"resume_text": st.session_state.resume_text, "requirement": prompt}, 
                                               timeout=300)
                        if response.status_code == 200:
                            roadmap = response.json()["roadmap"]
                            st.session_state.messages.append({"role": "assistant", "content": f"### 🗺️ Career Roadmap\n{roadmap}"})
                            st.session_state.step = "chat_loop"
                        else: st.error("Error from backend.")
                    except Exception as e: st.error(f"Error: {e}")
        else:
            # Handle general triggers
            if "jd" in prompt.lower() or "job description" in prompt.lower() or "gap" in prompt.lower():
                st.session_state.messages.append({"role": "assistant", "content": "Sure! Please **paste the Job Description (JD)** here so I can analyze the gap."})
                st.session_state.step = "awaiting_jd"
            elif "roadmap" in prompt.lower() or "path" in prompt.lower() or "goal" in prompt.lower():
                st.session_state.messages.append({"role": "assistant", "content": "I'd love to! What is your **target role or career goal**? (e.g., AI Architect)"})
                st.session_state.step = "awaiting_roadmap_target"
            else:
                # General ChatGPT-style chat
                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        try:
                            response = requests.post("http://localhost:8004/chat", 
                                                   json={"requirement": prompt, "resume_text": str(st.session_state.resume_text)}, 
                                                   timeout=300)
                            if response.status_code == 200:
                                chat_res = response.json()["response"]
                                st.session_state.messages.append({"role": "assistant", "content": chat_res})
                            else: st.error("Error from backend.")
                        except Exception as e: st.error(f"Error: {e}")
        
        st.rerun()
