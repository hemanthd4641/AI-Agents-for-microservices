import streamlit as st
import requests

API_URL = "http://localhost:8000/fitness"

def render_fitness_ui():
    st.title("🏋️ AI Fitness Studio")
    
    # Session State for Conversation
    for key, default in [("fit_messages", []), ("fit_data", {}), ("fit_initialized", False), ("fit_awaiting", None), ("fit_plan_mode", False)]:
        if key not in st.session_state: st.session_state[key] = default

    FIELD_QUESTIONS = {
        "goal": "What is your primary fitness goal? (e.g., Weight Loss, Muscle Gain, General Fitness)",
        "age": "How old are you?",
        "weight": "What is your current weight? (e.g., 75kg)",
        "height": "What is your height? (e.g., 180cm)",
        "equipment": "What equipment do you have access to? (Gym, Dumbbells, Bodyweight)",
        "diet_pref": "Any dietary preferences? (Vegetarian, Vegan, Keto, etc.)"
    }

    def missing_fields():
        return [f for f in FIELD_QUESTIONS.keys() if not st.session_state.fit_data.get(f)]

    if not st.session_state.fit_initialized:
        st.session_state.fit_messages.append({"role": "assistant", "content": "👋 Welcome to the **AI Fitness Studio**! I can answer your fitness questions or design a professional 7-day program for you. What's on your mind?"})
        st.session_state.fit_initialized = True

    # Display Chat History
    for msg in st.session_state.fit_messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    # Chat Input
    if prompt := st.chat_input("Ask a question or request a fitness plan..."):
        with st.chat_message("user"): st.markdown(prompt)
        st.session_state.fit_messages.append({"role": "user", "content": prompt})

        # Process Input
        if st.session_state.fit_awaiting:
            field = st.session_state.fit_awaiting
            st.session_state.fit_data[field] = prompt
            st.session_state.fit_awaiting = None
            st.rerun()
        else:
            with st.spinner("Thinking..."):
                try:
                    res = requests.post(f"{API_URL}/chat", json={"message": prompt})
                    if res.status_code == 200:
                        data = res.json()
                        parsed = data.get("parsed", {})
                        
                        # Update collected data
                        for k, v in parsed.items():
                            if k in FIELD_QUESTIONS and v and str(v).lower() not in ["null", "none", "false", "true"]:
                                st.session_state.fit_data[k] = v
                        
                        if "response" in data:
                            st.session_state.fit_messages.append({"role": "assistant", "content": data["response"]})
                        
                        if parsed.get("is_plan_request"):
                            st.session_state.fit_plan_mode = True
                            st.session_state.fit_messages.append({"role": "assistant", "content": "I'd be happy to build that plan for you! I just need a few details first."})
                        
                        st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    # Check for missing fields if we are in plan-mode
    if st.session_state.fit_plan_mode:
        remaining = missing_fields()
        if remaining:
            st.session_state.fit_awaiting = remaining[0]
            q = FIELD_QUESTIONS[remaining[0]]
            msg_content = f"**Step {len(st.session_state.fit_data)+1}/{len(FIELD_QUESTIONS)}**: {q}"
            # Check if last message was already this question to avoid duplicates
            if not st.session_state.fit_messages or st.session_state.fit_messages[-1]["content"] != msg_content:
                with st.chat_message("assistant"): st.markdown(msg_content)
                st.session_state.fit_messages.append({"role": "assistant", "content": msg_content})
        else:
            # All data collected, trigger plan generation
            with st.spinner("🚀 Our elite coaches are designing your 7-day program..."):
                try:
                    payload = st.session_state.fit_data
                    res = requests.post(f"{API_URL}/generate_plan", json=payload, timeout=300)
                    if res.status_code == 200:
                        plan = res.json().get("final_plan", "Error generating plan.")
                        st.session_state.fit_messages.append({"role": "assistant", "content": "✅ **Your Elite Fitness Program is Ready!**"})
                        st.session_state.fit_messages.append({"role": "assistant", "content": plan})
                        st.session_state.fit_plan_mode = False
                        st.session_state.fit_data = {} # Reset
                        st.rerun()
                except Exception as e:
                    st.error(f"Generation Error: {e}")
