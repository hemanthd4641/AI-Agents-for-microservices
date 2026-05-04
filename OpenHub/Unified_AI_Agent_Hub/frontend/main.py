import streamlit as st
from frontend.apps.fitness_ui import render_fitness_ui
from frontend.apps.placement_ui import render_placement_ui
from frontend.apps.research_ui import render_research_ui
from frontend.apps.travel_ui import render_travel_ui

st.set_page_config(
    page_title="Unified AI Agent Hub",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for premium look
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stSidebar {
        background-image: linear-gradient(#2d3436, #000000);
        color: white;
    }
    .stSidebar [data-testid="stMarkdownContainer"] p {
        color: white;
        font-size: 1.1rem;
    }
    .stButton>button {
        border-radius: 20px;
        background-color: #0984e3;
        color: white;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

def main():
    st.sidebar.title("🤖 AI Agent Hub")
    st.sidebar.markdown("Choose your specialized agent:")
    
    agent_choice = st.sidebar.radio(
        "Select Agent",
        ["🏋️ Fitness Studio", "💼 Placement Hub", "🔍 Research & Blog", "✈️ Travel Planner"],
        index=0,
        label_visibility="collapsed"
    )
    
    st.sidebar.markdown("---")
    st.sidebar.info("Powered by Groq & CrewAI")

    if agent_choice == "🏋️ Fitness Studio":
        render_fitness_ui()
    elif agent_choice == "💼 Placement Hub":
        render_placement_ui()
    elif agent_choice == "🔍 Research & Blog":
        render_research_ui()
    elif agent_choice == "✈️ Travel Planner":
        render_travel_ui()

if __name__ == "__main__":
    main()
