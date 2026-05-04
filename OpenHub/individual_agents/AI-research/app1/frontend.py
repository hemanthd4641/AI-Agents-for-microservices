import streamlit as st
import requests
import time

# Set Page Config
st.set_page_config(page_title="AI Research & Blog Agent", page_icon="📝", layout="wide")

# Custom Styling
st.markdown("""
    <style>
    .main {
        background-color: #0f172a;
        color: #f8fafc;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #3b82f6;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📝 AI Research & Content Strategist")
st.markdown("Powered by **CrewAI** and **Groq (Llama 3.1)**")

# Sidebar for history or settings
with st.sidebar:
    st.info("How it works: The Researcher finds data via Serper, then the Writer crafts a blog post.")
    if st.button("Clear History"):
        st.session_state.clear()

# Main Input
topic = st.text_input("Enter a topic you want to research and write about:", placeholder="e.g., The impact of AI on Job Markets")

if st.button("🚀 Generate Blog Post"):
    if not topic:
        st.warning("Please enter a topic!")
    else:
        with st.status("🔍 Agents are working... (Researching + Writing)", expanded=True) as status:
            try:
                # Call Backend with a long timeout (10 mins) for research
                start_time = time.time()
                response = requests.post("http://localhost:8001/generate_blog", 
                                       json={"topic": topic}, 
                                       timeout=600)
                
                if response.status_code == 200:
                    result = response.json()
                    status.update(label="✅ Blog Generation Complete!", state="complete", expanded=False)
                    
                    st.success(f"Generated in {round(time.time() - start_time, 2)} seconds")
                    
                    # Layout for results
                    st.markdown("---")
                    st.markdown(result["blog_post"])
                    
                    # Download option
                    st.download_button(
                        label="📥 Download as Markdown",
                        data=result["blog_post"],
                        file_name=f"{topic.replace(' ', '_')}_blog.md",
                        mime="text/markdown"
                    )
                else:
                    st.error(f"Error: {response.text}")
                    status.update(label="❌ Failed", state="error")
            except Exception as e:
                st.error(f"Could not connect to backend: {e}")
                status.update(label="❌ Connection Error", state="error")

# Footer
st.markdown("---")
st.caption("Built with ❤️ by AI Agents")
