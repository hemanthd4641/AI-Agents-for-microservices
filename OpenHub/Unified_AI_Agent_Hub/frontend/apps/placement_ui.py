import streamlit as st
import requests
import pdfplumber

API_BASE_URL = "http://localhost:8000/placement"

def extract_text_from_pdf(pdf_file):
    with pdfplumber.open(pdf_file) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text()
    return text

def render_placement_ui():
    st.title("💼 AI Placement Hub")
    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["🎯 Resume Audit", "🌉 Skill Gap Analysis", "🛣️ Career Roadmap"])

    with tab1:
        st.header("Resume Strategic Audit")
        uploaded_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"], key="audit_upload")
        if st.button("Analyze Resume", key="audit_btn"):
            if uploaded_file:
                text = extract_text_from_pdf(uploaded_file)
                with st.spinner("Analyzing..."):
                    res = requests.post(f"{API_BASE_URL}/analyze_resume", json={"resume_text": text})
                    st.markdown(res.json().get("analysis", "Error"))

    with tab2:
        st.header("Skill Gap Bridge")
        col1, col2 = st.columns(2)
        with col1:
            res_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"], key="gap_res")
        with col2:
            jd_text = st.text_area("Job Description", placeholder="Paste JD here...")
        
        if st.button("Find Gaps", key="gap_btn"):
            if res_file and jd_text:
                text = extract_text_from_pdf(res_file)
                with st.spinner("Mapping gaps..."):
                    res = requests.post(f"{API_BASE_URL}/skill_gap", json={"resume_text": text, "jd_text": jd_text})
                    st.markdown(res.json().get("gap_report", "Error"))

    with tab3:
        st.header("🛣️ Elite Career Architect")
        st.caption("Ask general career questions or request a full 6-month roadmap!")
        
        # Initialize chat history
        if "placement_chat_history" not in st.session_state:
            st.session_state.placement_chat_history = [
                {"role": "assistant", "content": "👋 I'm your Elite Career Architect. How can I help you reach the top 1% today?"}
            ]

        # Display chat messages
        for message in st.session_state.placement_chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Chat Input
        if prompt := st.chat_input("e.g., 'How do I become a Senior AI Engineer?' or 'Give me a roadmap for DevOps'"):
            # Display user message
            with st.chat_message("user"):
                st.markdown(prompt)
            st.session_state.placement_chat_history.append({"role": "user", "content": prompt})

            # Get AI response
            with st.spinner("Architecting your career..."):
                try:
                    res = requests.post(
                        f"{API_BASE_URL}/career_roadmap", 
                        json={"resume_text": "", "requirement": prompt}
                    )
                    response_text = res.json().get("roadmap", "I encountered an error planning your career.")
                    
                    with st.chat_message("assistant"):
                        st.markdown(response_text)
                    st.session_state.placement_chat_history.append({"role": "assistant", "content": response_text})
                except Exception as e:
                    st.error(f"Failed to connect to mentor: {e}")
