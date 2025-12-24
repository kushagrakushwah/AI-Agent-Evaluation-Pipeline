import streamlit as st
import requests
import json
import pandas as pd
import plotly.express as px
import os

# --- CONFIG ---
st.set_page_config(page_title="Pro Agent Eval Pipeline", layout="wide")
API_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# --- CUSTOM CSS FOR PROFESSIONAL LOOK ---
st.markdown("""
    <style>
    .metric-card {
        background-color: #0E1117;
        border: 1px solid #30333F;
        border-radius: 5px;
        padding: 15px;
        margin-bottom: 10px;
    }
    .success { color: #00CC96; }
    .fail { color: #EF553B; }
    .warning { color: #FFA15A; }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ AI Agent Evaluation Pipeline (Production)")

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["🚀 Live Evaluation", "📊 Inter-Annotator Agreement", "🔧 System Health"])

# --- TAB 1: RUNNER ---
with tab1:
    col1, col2 = st.columns([1, 1.2])
    
    with col1:
        st.subheader("📥 Ingestion Layer")
        
        # Scenario Selector for Demo Convenience
        scenario = st.selectbox("Select Test Scenario:", 
            ["Custom JSON", "Scenario: Refund (Missing Tool)", "Scenario: Flight (Perfect)", "Scenario: Empty Message"])
        
        if scenario == "Scenario: Refund (Missing Tool)":
            default_json = {
                "id": "log_refund_fail_001",
                "messages": [
                    {"role": "user", "content": "I want a refund for order #999."},
                    {"role": "assistant", "content": "Sure, I can help with that. What is the issue?"}
                ]
            }
        elif scenario == "Scenario: Flight (Perfect)":
            default_json = {
                "id": "log_flight_success_001",
                "messages": [
                    {"role": "user", "content": "Book a flight to Paris on Friday."},
                    {"role": "assistant", "content": "Checking flights...", 
                     "tool_calls": [{"id": "call_1", "name": "flight_search", "arguments": {"destination": "Paris", "date": "Friday"}}]},
                    {"role": "tool", "content": "Flight found: BA123"},
                    {"role": "assistant", "content": "I found flight BA123."}
                ]
            }
        elif scenario == "Scenario: Empty Message":
             default_json = {
                "id": "log_empty_001",
                "messages": [{"role": "user", "content": ""}]
            }
        else:
            default_json = {"id": "custom", "messages": [{"role": "user", "content": "Hello"}]}

        json_input = st.text_area("Conversation Log (JSON)", value=json.dumps(default_json, indent=2), height=400)
        
        if st.button("🚀 Run Pipeline", type="primary"):
            try:
                payload = json.loads(json_input)
                with st.spinner("Processing in Async Queue..."):
                    res = requests.post(f"{API_URL}/ingest", json=payload)
                
                if res.status_code == 200:
                    st.session_state['last_result'] = res.json()
                    st.success("Ingested & Evaluated Successfully")
                else:
                    st.error(f"Backend Error ({res.status_code}): {res.text}")
            except Exception as e:
                st.error(f"Connection Failed: {e}")

    with col2:
        st.subheader("🔍 Deep-Dive Analysis")
        
        if 'last_result' in st.session_state:
            data = st.session_state['last_result']
            
            # 1. Top Level Score
            score = data['aggregated_score']
            color = "green" if score > 0.8 else "red" if score < 0.5 else "orange"
            st.markdown(f"### Aggregate Quality Score: :{color}[{score:.2f} / 1.0]")
            st.progress(score)
            
            st.divider()
            
            # 2. Metric Breakdown
            st.markdown("#### 🔬 Evaluator Details")
            for m in data['metrics']:
                with st.container():
                    c1, c2 = st.columns([1, 4])
                    c1.metric(label=m['evaluator'].replace("_", " ").title(), value=f"{m['score']:.2f}")
                    c2.info(f"**Reasoning:** {m['reasoning']}")
            
            st.divider()
            
            # 3. Improvement Engine (Self-Correction)
            st.markdown("#### 💡 Automated Suggestions")
            if data['suggestions']:
                for s in data['suggestions']:
                    with st.expander(f"Update Target: {s['target'].upper()} (Click to Expand)", expanded=True):
                        st.markdown(f"**Action:** {s['suggestion']}")
                        st.markdown(f"**Rationale:** *{s['rationale']}*")
                        st.caption(f"Expected Impact: {s['expected_impact']}")
            else:
                st.success("No issues detected. System performing optimally.")

            # 4. Human Loop
            st.divider()
            st.markdown("#### 👤 Human Ground Truth")
            human_score = st.slider("Rate this conversation:", 0.0, 1.0, 0.5)
            if st.button("Submit Human Annotation"):
                fb_payload = {
                    "conversation_id": data['conversation_id'],
                    "annotator_id": "reviewer_1",
                    "score": human_score,
                    "labels": [],
                    "confidence": 1.0
                }
                requests.post(f"{API_URL}/feedback", json=fb_payload)
                st.success("Feedback stored for Agreement Calculation.")

# --- TAB 2: META-EVAL ---
with tab2:
    st.header("Annotator Agreement (Cohen's Kappa Proxy)")
    if st.button("Calculate Inter-Annotator Agreement"):
        try:
            res = requests.get(f"{API_URL}/metrics/agreement").json()
            st.metric("Agreement Index", f"{res['inter_annotator_agreement']}", delta=res['method'])
            st.info("Higher score (near 1.0) indicates high consensus among human annotators.")
        except Exception as e:
            st.error(e)

# --- TAB 3: HEALTH ---
with tab3:
    st.json({"status": "healthy", "mode": "async", "backend": API_URL})