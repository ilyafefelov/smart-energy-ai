"""
Enhanced Dashboard with Real Solar Data, Prices, and Model Versions
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import sys
import os

# Add project root
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from src.enhanced_config import get_config
from src.oree_fixed_scraper import OREEEffectiveScraper

# Configure page
st.set_page_config(page_title="Smart Energy Dashboard", layout="wide", initial_sidebar_state="expanded")

# ═══════════════════════════════════════════════════════════════
# INITIALIZATION
# ═══════════════════════════════════════════════════════════════

config = get_config()
current_hour = datetime.now().hour
current_date = datetime.now().strftime("%Y-%m-%d")

# ═══════════════════════════════════════════════════════════════
# HEADER WITH VERSION
# ═══════════════════════════════════════════════════════════════

col_title, col_version, col_retrain = st.columns([2, 1, 1])

with col_title:
    st.title("📊 Smart Energy AI Dashboard")
    st.markdown("*Real-time optimization with AI*")

with col_version:
    current_version = config.get_current_version()
    st.metric("Model Version", current_version)

with col_retrain:
    # Get last training time
    history = config.get_version_history()
    if history:
        last_trained = history[0].trained_at[:10]  # YYYY-MM-DD
        st.metric("Last Trained", last_trained)

# ═══════════════════════════════════════════════════════════════
# DATA FETCHERS
# ═══════════════════════════════════════════════════════════════

@st.cache_data(ttl=300)
def fetch_prices():
    """Fetch OREE prices with fallback"""
    try:
        scraper = OREEEffectiveScraper(use_cache=True)
        prices_df = scraper.fetch_today_prices()
        if prices_df is not None and len(prices_df) > 0:
            return prices_df
    except Exception as e:
        st.warning(f"⚠️ OREE API: {str(e)[:80]}")
    
    # Fallback
    from src.price_fallback import get_sample_prices
    return get_sample_prices()

@st.cache_data(ttl=3600)
def fetch_solar():
    """Fetch solar data with fallback"""
    try:
        from src.solar_data import get_solar_fetcher
        fetcher = get_solar_fetcher()
        return {
            'current': fetcher.get_current_solar_irradiance(),
            'forecast_24h': fetcher.get_hourly_forecast_24h(),
            'status': 'live'
        }
    except Exception as e:
        st.warning(f"⚠️ Solar API: {str(e)[:80]}")
        return None

prices_df = fetch_prices()
solar_data = fetch_solar()

# ═══════════════════════════════════════════════════════════════
# CURRENT CONDITIONS
# ═══════════════════════════════════════════════════════════════

st.subheader("📈 Current Market & Solar Conditions")

if prices_df is not None and len(prices_df) > 0:
    current_price_eur = prices_df.iloc[min(current_hour, len(prices_df)-1)]['price_eur_mwh']
    current_price_uah = prices_df.iloc[min(current_hour, len(prices_df)-1)]['price_uah_mwh']
    avg_price_eur = prices_df['price_eur_mwh'].mean()
    
    col_metrics = st.columns(6)
    
    with col_metrics[0]:
        st.metric(
            "Current Price",
            f"€{current_price_eur:.2f}/MWh",
            help="OREE market price"
        )
    
    with col_metrics[1]:
        st.metric(
            "₴ Price (UAH)",
            f"₴{current_price_uah:.0f}",
            help="Exchange rate: ~€1=₴35"
        )
    
    with col_metrics[2]:
        st.metric(
            "Daily Avg",
            f"€{avg_price_eur:.2f}",
            help="Average price today"
        )
    
    with col_metrics[3]:
        optimizer_cfg = config.get_optimizer_config()
        cheap = optimizer_cfg.get('cheap_price_threshold_eur', 3.0)
        expensive = optimizer_cfg.get('expensive_price_threshold_eur', 8.0)
        
        if current_price_eur < cheap:
            status = "💚 CHEAP"
        elif current_price_eur > expensive:
            status = "❤️ EXPENSIVE"
        else:
            status = "🟡 NORMAL"
        
        st.metric("Market Status", status)
    
    # Solar metrics
    if solar_data and solar_data['current']:
        current_solar = solar_data['current']
        irradiance = current_solar.get('irradiance_w_m2', 0)
        generation_kw = (irradiance * 20 / 1000) * 0.18  # 20kW system
        
        with col_metrics[4]:
            st.metric(
                "Solar Irradiance",
                f"{irradiance:.0f} W/m²",
                help="Real-time sunlight intensity"
            )
        
        with col_metrics[5]:
            st.metric(
                "Est. Solar Gen",
                f"{generation_kw:.2f} kW",
                help="20kW system output"
            )
    else:
        with col_metrics[4]:
            st.metric("Solar Status", "⚠️ Unavailable")

st.divider()

# ═══════════════════════════════════════════════════════════════
# PRICE FORECAST GRAPH
# ═══════════════════════════════════════════════════════════════

if prices_df is not None and len(prices_df) > 0:
    st.subheader("⏰ 24-Hour Price Forecast (EUR/MWh)")
    
    fig_price = go.Figure()
    
    fig_price.add_trace(go.Scatter(
        x=prices_df['hour'],
        y=prices_df['price_eur_mwh'],
        name="Price",
        mode='lines+markers',
        line=dict(color='#2E86AB', width=3),
        fill='tozeroy',
        fillcolor='rgba(46, 134, 171, 0.2)',
        marker=dict(size=8),
        hovertemplate='<b>Hour %{x}:00</b><br>€%{y:.2f}/MWh<extra></extra>'
    ))
    
    # Add thresholds
    optimizer_cfg = config.get_optimizer_config()
    cheap = optimizer_cfg.get('cheap_price_threshold_eur', 3.0)
    expensive = optimizer_cfg.get('expensive_price_threshold_eur', 8.0)
    
    fig_price.add_hline(y=cheap, line_dash="dash", line_color="green", 
                        annotation_text="Cheap", annotation_position="right")
    fig_price.add_hline(y=expensive, line_dash="dash", line_color="red",
                        annotation_text="Expensive", annotation_position="right")
    
    fig_price.update_layout(
        xaxis_title="Hour of Day",
        yaxis_title="Price (EUR/MWh)",
        height=350,
        hovermode='x unified',
        template='plotly_white'
    )
    
    st.plotly_chart(fig_price, use_container_width=True)

st.divider()

# ═══════════════════════════════════════════════════════════════
# SOLAR FORECAST
# ═══════════════════════════════════════════════════════════════

if solar_data and solar_data['forecast_24h'] is not None:
    st.subheader("☀️  24-Hour Solar Generation Forecast")
    
    forecast_df = solar_data['forecast_24h']
    
    fig_solar = go.Figure()
    
    fig_solar.add_trace(go.Bar(
        x=forecast_df['hour'],
        y=forecast_df['generation_forecast_kw'],
        name="Solar Generation",
        marker=dict(color='#F7B801'),
        hovertemplate='<b>Hour %{x}:00</b><br>%{y:.2f} kW<extra></extra>'
    ))
    
    fig_solar.update_layout(
        xaxis_title="Hour of Day",
        yaxis_title="Generation (kW)",
        height=300,
        hovermode='x unified',
        template='plotly_white'
    )
    
    st.plotly_chart(fig_solar, use_container_width=True)

st.divider()

# ═══════════════════════════════════════════════════════════════
# VERSION HISTORY
# ═══════════════════════════════════════════════════════════════

st.subheader("📌 Model Version History")

history = config.get_version_history()
if history:
    for i, version in enumerate(history[:5]):  # Show last 5
        with st.expander(f"v{version.version} - {version.trained_at[:10]}", open=(i==0)):
            col_v1, col_v2, col_v3 = st.columns(3)
            
            with col_v1:
                st.metric("Episodes", version.episodes)
                st.metric("Avg Reward", f"{version.avg_reward:.2f}")
            
            with col_v2:
                st.metric("Best Reward", f"{version.best_reward:.2f}")
                st.metric("Training Time", f"{version.training_time_seconds:.1f}s")
            
            with col_v3:
                st.metric("Model Path", version.model_path.split('\\')[-1])
                if version.notes:
                    st.caption(f"📝 {version.notes}")
else:
    st.info("No training history yet. Train a model in the Configuration page.")

st.divider()

# ═══════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════

st.subheader("💡 AI Recommendation")

if prices_df is not None and len(prices_df) > 0:
    if current_price_eur < cheap:
        st.success("""
        **CHARGE BATTERY** 💡
        - Current price is low (€{:.2f})
        - Store energy for later use
        - Expected savings: 3-5x in peak hours
        """.format(current_price_eur))
    elif current_price_eur > expensive:
        st.error("""
        **DISCHARGE & SELL** ⚡
        - Current price is high (€{:.2f})
        - Sell battery energy to grid
        - Expected revenue: €{:.2f}/kWh
        """.format(current_price_eur, current_price_eur/1000))
    else:
        st.warning("""
        **HOLD** ⏳
        - Current price is average (€{:.2f})
        - Wait for cheaper pricing
        - Next cheapest hours: 2-4 AM
        """.format(current_price_eur))
