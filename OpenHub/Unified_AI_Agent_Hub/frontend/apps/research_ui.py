import streamlit as st
import requests

API_URL = "http://localhost:8000/research/generate_blog"

def render_research_ui():
    st.title("🔍 AI Research & Blog Writer")
    st.markdown("---")

    topic = st.text_input("Enter Topic", placeholder="e.g., Future of Agentic AI")

    if st.button("Generate Blog Post", width="stretch"):
        if not topic:
            st.warning("Please enter a topic.")
        else:
            with st.spinner(f"Researching and writing about '{topic}'..."):
                try:
                    res = requests.post(API_URL, json={"topic": topic}, timeout=300)
                    if res.status_code == 200:
                        blog = res.json().get("blog_post", "No post generated.")
                        st.success("✅ Research and Writing Complete!")
                        st.markdown(blog)
                    else:
                        st.error(f"Error: {res.text}")
                except Exception as e:
                    st.error(f"Connection Error: {e}")
