import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime
import sys

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

# --- IMPORT TRAINING ANALYZER ---
sys.path.insert(0, current_dir)
from src.training_analyzer import generate_training_data

# --- TABS FOR NAVIGATION ---
tab_dashboard, tab_training, tab_guide = st.tabs(["📊 Dashboard", "🤖 Training", "📖 Technical Guide"])

with tab_dashboard:
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

with tab_training:
    st.title("🤖 RL Agent Training Dashboard")
    
    # Load training data
    training_data = generate_training_data()
    summary = training_data['summary']
    df_training = training_data['dataframe']
    report = training_data['report']
    
    # --- TOP METRICS ---
    st.subheader("📊 Training Summary")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Episodes", summary['total_episodes'], delta=None)
    with col2:
        st.metric("Baseline Cost", f"{summary['baseline_cost']:,.0f} UAH")
    with col3:
        st.metric("Final Cost", f"{summary['final_cost']:,.0f} UAH", delta=f"{-summary['cost_reduction_pct']:.1f}%")
    with col4:
        st.metric("Daily Savings", f"{summary['baseline_cost'] - summary['final_cost']:,.0f} UAH")
    with col5:
        st.metric("Yearly Savings", f"{(summary['baseline_cost'] - summary['final_cost']) * 365 / 1_000_000:.1f}M UAH")
    
    st.markdown("---")
    
    # --- TRAINING GRAPHS ---
    st.subheader("📈 Training Metrics")
    
    col_graph1, col_graph2 = st.columns(2)
    
    with col_graph1:
        # Cost reduction over time
        fig_cost = go.Figure()
        fig_cost.add_trace(go.Scatter(
            x=df_training['episode'],
            y=df_training['cost'],
            mode='lines+markers',
            name='Episode Cost',
            line=dict(color='#e74c3c', width=2),
            marker=dict(size=5)
        ))
        fig_cost.add_trace(go.Scatter(
            x=df_training['episode'],
            y=df_training['moving_avg_cost'],
            mode='lines',
            name='Moving Average (5 episodes)',
            line=dict(color='#3498db', width=3, dash='dash')
        ))
        fig_cost.add_hline(y=summary['baseline_cost'], line_dash="dash", line_color="gray", 
                          annotation_text="Baseline", annotation_position="right")
        fig_cost.update_layout(
            title="💰 Cost Reduction During Training",
            xaxis_title="Episode",
            yaxis_title="Daily Cost (UAH)",
            hovermode='x unified',
            height=400
        )
        st.plotly_chart(fig_cost, use_container_width=True)
    
    with col_graph2:
        # Improvement percentage over time
        fig_improvement = go.Figure()
        fig_improvement.add_trace(go.Scatter(
            x=df_training['episode'],
            y=df_training['improvement'],
            mode='lines+markers',
            name='Improvement %',
            fill='tozeroy',
            line=dict(color='#2ecc71', width=2),
            marker=dict(size=5)
        ))
        fig_improvement.add_hline(y=30, line_dash="dash", line_color="orange", 
                                 annotation_text="Target (30%)", annotation_position="right")
        fig_improvement.update_layout(
            title="📈 Cost Improvement Percentage",
            xaxis_title="Episode",
            yaxis_title="Improvement (%)",
            hovermode='x unified',
            height=400
        )
        st.plotly_chart(fig_improvement, use_container_width=True)
    
    # --- REWARD ANALYSIS ---
    col_graph3, col_graph4 = st.columns(2)
    
    with col_graph3:
        # Reward over time
        fig_reward = go.Figure()
        fig_reward.add_trace(go.Scatter(
            x=df_training['episode'],
            y=df_training['reward'],
            mode='lines+markers',
            name='Episode Reward',
            line=dict(color='#9b59b6', width=2),
            marker=dict(size=5)
        ))
        fig_reward.add_trace(go.Scatter(
            x=df_training['episode'],
            y=df_training['avg_reward'],
            mode='lines',
            name='Average Reward',
            line=dict(color='#f39c12', width=3)
        ))
        fig_reward.update_layout(
            title="🎯 Reward During Training",
            xaxis_title="Episode",
            yaxis_title="Reward (higher is better)",
            hovermode='x unified',
            height=400
        )
        st.plotly_chart(fig_reward, use_container_width=True)
    
    with col_graph4:
        # Learning rate analysis
        fig_learning = go.Figure()
        fig_learning.add_trace(go.Scatter(
            x=df_training['episode'],
            y=df_training['cost'].diff().fillna(0),
            mode='lines+markers',
            name='Cost Change',
            line=dict(color='#e67e22', width=2),
            marker=dict(size=4)
        ))
        fig_learning.axhline(y=0, line_dash="dash", line_color="black")
        fig_learning.update_layout(
            title="📉 Episode-to-Episode Change",
            xaxis_title="Episode",
            yaxis_title="Cost Difference (UAH)",
            hovermode='x unified',
            height=400
        )
        st.plotly_chart(fig_learning, use_container_width=True)
    
    st.markdown("---")
    
    # --- PERFORMANCE STATISTICS ---
    st.subheader("📊 Performance Statistics")
    
    stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)
    
    with stats_col1:
        st.markdown(f"""
        **Convergence Speed**
        
        Episode {summary['convergence_speed']}
        
        Agent reached 80% of best performance
        """)
    
    with stats_col2:
        st.markdown(f"""
        **Training Stability**
        
        {summary['stability_score']:.1f}%
        
        Measures variance in recent episodes
        """)
    
    with stats_col3:
        st.markdown(f"""
        **Peak Performance**
        
        {summary['best_reduction_pct']:.1f}%
        
        Best cost reduction achieved
        """)
    
    with stats_col4:
        st.markdown(f"""
        **Consistency**
        
        {abs(summary['avg_cost'] - summary['final_cost']):,.0f} UAH
        
        Variance from average cost
        """)
    
    st.markdown("---")
    
    # --- DETAILED REPORT ---
    st.subheader("📋 Detailed Training Report")
    
    if st.checkbox("📖 Show Full Training Report"):
        st.text(report)
    
    # --- DATA TABLE ---
    st.subheader("📊 Training Data")
    st.dataframe(df_training.style.format({
        'cost': '{:,.0f}',
        'reward': '{:.2f}',
        'improvement': '{:.1f}',
        'avg_reward': '{:.2f}',
        'moving_avg_cost': '{:,.0f}'
    }), use_container_width=True)
    
    # --- STRATEGY EXPLANATION ---
    st.subheader("💡 What the Agent Learned")
    
    strategy_col1, strategy_col2 = st.columns(2)
    
    with strategy_col1:
        st.markdown("""
        ### Daily Schedule Strategy
        
        🌙 **Night (00:00-06:00)**
        - Charge battery from cheap grid
        - Lowest prices of the day
        - Cost: ~2.0-2.8 EUR/MWh
        
        ☀️ **Morning (06:00-10:00)**
        - Store solar energy in battery
        - Solar generation starts
        - Battery prepares for peak
        
        ☀️ **Noon (10:00-15:00)**
        - Sell excess solar to grid
        - Peak solar generation
        - Generate profit when possible
        """)
    
    with strategy_col2:
        st.markdown("""
        ### Peak Management
        
        💰 **Evening Peak (15:00-21:00)**
        - Discharge battery at high prices
        - Cost avoidance strategy
        - Prices peak: ~9-11 EUR/MWh
        
        🌙 **Late Night (21:00-24:00)**
        - Top-up battery for next day
        - Prepare for morning solar
        - Lowest night prices
        
        🎯 **Overall Goal**
        - Buy cheap (night rates)
        - Store free (solar)
        - Sell high (grid peak)
        - Minimize: grid purchases during peak
        """)

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
    ├── app.py                      # This interface
    ├── src/
    │   ├── rl_environment.py       # Gym environment
    │   ├── rl_training.py          # Training script
    │   ├── training_analyzer.py    # Analytics
    │   └── price_processor.py      # Data processing
    └── data/                       # Training data
    """)
    
    st.subheader("3. RL Training Process")
    st.markdown("""
    The agent uses **PPO (Proximal Policy Optimization)** to learn optimal energy management:
    
    - **Input State**: Temperature, Solar, Cloud Cover, Price, Battery Level
    - **Output Actions**: Charge Rate, Discharge Rate, Grid Buy, Grid Sell
    - **Reward**: Minimize daily electricity cost
    - **Training**: 50 episodes × 24 hours = 1,200 timesteps
    """)
    
    st.subheader("4. Data Sources")
    st.write("- **Weather:** Real Open-Meteo data (Kyiv, Ukraine)")
    st.write("- **Market:** Realistic OREE DAM prices (70-402 UAH/MWh)")
    st.write("- **Analysis:** 7-day historical patterns")
