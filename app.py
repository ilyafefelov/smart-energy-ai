import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime

st.set_page_config(page_title="Smart Energy AI Enterprise", layout="wide")

# --- DATA LOADING ---
file_map = {"Normal": "opt_normal.csv", "Winter": "opt_winter.csv", "Blackout": "opt_blackout.csv"}
scenario = st.sidebar.selectbox("Select Scenario", ["Normal", "Winter", "Blackout"])

# Get correct paths based on where app.py is running from
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
data_processed = os.path.join(current_dir, "data", "processed", file_map[scenario])
data_raw = os.path.join(current_dir, "data", "raw", "weather_forecast.csv")

df = pd.read_csv(data_processed)
weather_df = pd.read_csv(data_raw)

# --- TABS FOR NAVIGATION ---
tab_dashboard, tab_guide = st.tabs(["📊 Dashboard", "📖 Technical Guide"])

with tab_dashboard:
    # --- (Previous Dashboard Code) ---
    current_hour_actual = datetime.now().hour
    current_hour = st.sidebar.slider("System Hour", 0, 23, current_hour_actual)

    row = df[df['Hour'] == current_hour].iloc[0]
    prev_row = df[df['Hour'] == (current_hour - 1 if current_hour > 0 else 0)].iloc[0]

    action = row['Action']
    price = row['Price']
    soc = row['SOC']
    
    st.title(f"🏢 EMS: {scenario} Mode")
    
    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        bg_color = "#2ecc71" if "SELL" in action or "STORE" in action else "#e74c3c" if "BUY" in action else "#f1c40f"
        if "DISCHARGE" in action: bg_color = "#3498db"
        if "CHARGE FROM GRID" in action: bg_color = "#9b59b6"
        st.markdown(f'<div style="background-color: {bg_color}; padding: 20px; border-radius: 10px; text-align: center; color: white;"><p style="margin:0; font-size: 14px; opacity: 0.8;">CURRENT STRATEGY</p><p style="margin:0; font-size: 26px; font-weight: bold;">{action}</p></div>', unsafe_allow_html=True)
    
    with col_b: st.metric("Market Price", f"{price} UAH")
    with col_c: st.metric("Solar Production", f"{row['Solar']} kW")
    with col_d: st.metric("Battery State", f"{soc}%")

    st.plotly_chart(px.bar(df, x='Hour', y=[1]*24, color='Action', title="Strategy Timeline"), use_container_width=True)
    
    fig_full = go.Figure()
    fig_full.add_trace(go.Scatter(x=df['Hour'], y=df['Price'], name="Price", yaxis="y2"))
    fig_full.add_trace(go.Bar(x=df['Hour'], y=df['Solar'], name="Solar"))
    fig_full.add_trace(go.Scatter(x=df['Hour'], y=df['SOC'], name="SOC %"))
    fig_full.update_layout(yaxis2=dict(overlaying="y", side="right"))
    st.plotly_chart(fig_full, use_container_width=True)

with tab_guide:
    st.header("📘 How to use this System")
    
    st.subheader("1. Strategic Concepts")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        - 🔴 **BUY FROM GRID**: Forced purchase. Required when solar and battery are empty.
        - 🟣 **CHARGE FROM GRID**: Strategic investment. Buying energy at night prices to save later.
        - 🔵 **DISCHARGE BATTERY**: Cost avoidance. Using stored power during evening peaks.
        """)
    with col2:
        st.markdown("""
        - 🟢 **SELL TO GRID**: Profit generation. Selling excess energy when battery is full.
        - 🟡 **STORE SOLAR**: Efficiency. Capturing free solar energy for evening use.
        """)
        
    st.subheader("2. Project Architecture")
    st.code("""
    projects/smart-energy-ai/
    ├── app.py              # This interface
    ├── src/
    │   ├── weather.py      # Real-time data fetch
    │   └── optimizer.py    # ML Logic
    └── data/               # Simulation logs
    """)
    
    st.subheader("3. Data Sources")
    st.write("- **Weather:** Real-time data from Open-Meteo (Kyiv coordinates).")
    st.write("- **Market:** Simulated Ukrainian Day-Ahead Market (DAM) prices.")
    st.write("- **Analysis Depth:** 72-hour sliding window.")
