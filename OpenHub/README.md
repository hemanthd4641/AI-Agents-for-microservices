# 🌟 Unified AI Agent Hub

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white" alt="Streamlit">
  <img src="https://img.shields.io/badge/LLM-Llama%203%20%7C%20Gemini-orange.svg" alt="LLMs">
</div>
<br>

A comprehensive, full-stack platform that consolidates multiple specialized AI agents into a single, cohesive interface. Built with a high-performance FastAPI backend and an interactive Streamlit frontend, this hub allows users to seamlessly navigate between different conversational AI assistants tailored for specific real-world tasks. 

---

## ✨ Features

The **Unified AI Agent Hub** is a comprehensive platform that brings together four specialized, conversational AI assistants into a single, seamless user experience. 

- 🎓 **AI Placement Hub**: Helps users navigate their job search by providing deep resume analysis, ATS scoring, skill gap identification, and personalized, step-by-step career roadmaps for interview preparation.
- ✈️ **AI Travel Planner**: Intuitively understands user preferences to generate complete, multi-city travel itineraries covering flights, road trips, and rail journeys.
- 🏋️ **AI Fitness Studio**: Acts as a personal health coach, designing tailored workout routines and dietary plans based on individual goals and physical constraints.
- 📝 **AI Research & Blog Generator**: Automates the process of information gathering and content creation, allowing users to effortlessly draft well-structured articles.

Together, these agents provide a powerful, centralized suite of tools designed to boost productivity, health, and career growth.

---

## 🛠️ Technology Stack

- **Frontend**: Streamlit (Dynamic, conversational, multi-page UI)
- **Backend**: FastAPI (High-performance API routing and state management)
- **AI/LLM Engine**: Provider-agnostic design (currently utilizing state-of-the-art LLMs like Llama 3 / Gemini)

---

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- API Keys for your preferred LLM provider (e.g., Groq, Google Gemini)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/hemanthd4641/AI-Agents-for-microservices.git
   cd AI-Agents-for-microservices/Unified_AI_Agent_Hub
   ```

2. **Set up a virtual environment (Recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables:**
   Create a `.env` file in the root directory and add your API keys:
   ```ini
   # LLM API Keys
   GROQ_API_KEY=your_groq_api_key
   GEMINI_API_KEY=your_gemini_api_key
   ```

### Running the Hub

You can launch both the FastAPI backend and the Streamlit frontend with a single command!

```bash
python run_hub.py
```

This script will automatically:
1. Start the **FastAPI Backend** on `http://localhost:8000`
2. Wait for the backend to warm up
3. Launch the **Streamlit Frontend** in your default web browser

---

## 🏗️ Architecture overview

- `backend/`: Houses the FastAPI application, core routing logic, and individual agent logic (`travel.py`, `fitness.py`, `placement.py`, etc.).
- `frontend/`: Contains the Streamlit entry point (`main.py`) and individual UI modules for each agent inside the `apps/` directory.
- `run_hub.py`: The central orchestration script to initialize both services synchronously.

---

> Built with ❤️ to demonstrate the power of orchestrating multiple LLM microservices into a stable, production-ready web application.
