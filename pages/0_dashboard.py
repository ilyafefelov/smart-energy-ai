"""
Enhanced Dashboard with Prices (with units) and Retraining Integration
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
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
st.set_page_config(page_title="Dashboard", layout="wide", initial_sidebar_state="expanded")

# Initialize session state
if 'model_version' not in st.session_state:
    st.session_state.model_version = "1.0.0"

if 'last_retrain' not in st.session_state:
    st.session_state.last_retrain = "2026-01-29 17:00:00"

# ═══════════════════════════════════════════════════════════════
# HEADER & INFO
# ═══════════════════════════════════════════════════════════════

col_title, col_status = st.columns([3, 1])

with col_title:
    st.title("📊 Smart Energy AI Dashboard")
    st.markdown("Real-time optimization and predictions")

with col_status:
    st.metric("Model Version", st.session_state.model_version)

config = get_config()

# Get current time
current_hour = datetime.now().hour
current_date = datetime.now().strftime("%Y-%m-%d")

# ═══════════════════════════════════════════════════════════════
# FETCH REAL PRICES
# ═══════════════════════════════════════════════════════════════

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_oree_prices():
    """Fetch REAL OREE prices"""
    try:
        scraper = OREEEffectiveScraper(use_cache=True)
        prices_df = scraper.fetch_today_prices()
        if prices_df is not None and len(prices_df) > 0:
            return prices_df
    except Exception as e:
        st.warning(f"Could not fetch live OREE prices: {str(e)[:100]}")
    
    # Fallback to sample data if needed
    from src.price_fallback import get_sample_prices
    return get_sample_prices()

prices_df = get_oree_prices()

# ═══════════════════════════════════════════════════════════════
# TOP METRICS
# ═══════════════════════════════════════════════════════════════

st.subheader("📈 Current Market Conditions")

if prices_df is not None and len(prices_df) > 0:
    current_price_eur = prices_df.iloc[current_hour]['price_eur_mwh']
    current_price_uah = prices_df.iloc[current_hour]['price_uah_mwh']
    avg_price_eur = prices_df['price_eur_mwh'].mean()
    min_price_eur = prices_df['price_eur_mwh'].min()
    max_price_eur = prices_df['price_eur_mwh'].max()
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "Current Price",
            f"€{current_price_eur:.2f}/MWh",
            delta=f"₴{current_price_uah:.0f}/MWh",
            help="Current OREE market price"
        )
    
    with col2:
        st.metric(
            "Daily Average",
            f"€{avg_price_eur:.2f}/MWh",
            help="Average price for the day"
        )
    
    with col3:
        st.metric(
            "Daily Low",
            f"€{min_price_eur:.2f}/MWh",
            help="Lowest price point"
        )
    
    with col4:
        st.metric(
            "Daily High",
            f"€{max_price_eur:.2f}/MWh",
            help="Highest price point"
        )
    
    with col5:
        # Get threshold from optimizer config
        optimizer_cfg = config.get_optimizer_config()
        cheap_threshold = optimizer_cfg.get('cheap_price_threshold_eur', 3.0)
        expensive_threshold = optimizer_cfg.get('expensive_price_threshold_eur', 8.0)
        
        if current_price_eur < cheap_threshold:
            st.metric("Status", "💚 CHEAP", help="Good time to buy")
        elif current_price_eur > expensive_threshold:
            st.metric("Status", "❤️ EXPENSIVE", help="Good time to sell")
        else:
            st.metric("Status", "🟡 NORMAL", help="Medium prices")
else:
    st.error("❌ Could not load price data")

st.divider()

# ═══════════════════════════════════════════════════════════════
# PRICE CHART WITH UNITS
# ═══════════════════════════════════════════════════════════════

if prices_df is not None and len(prices_df) > 0:
    
    col_chart, col_info = st.columns([3, 1])
    
    with col_chart:
        st.subheader("⏰ 24-Hour Price Schedule")
        
        # Create dual-axis chart (EUR and UAH)
        fig = go.Figure()
        
        # EUR prices (primary axis)
        fig.add_trace(go.Scatter(
            x=prices_df['hour'],
            y=prices_df['price_eur_mwh'],
            name="Price (EUR/MWh)",
            mode='lines+markers',
            line=dict(color='#2E86AB', width=3),
            marker=dict(size=8),
            hovertemplate='<b>Hour %{x}:00</b><br>' +
                         'Price: €%{y:.2f}/MWh<br>' +
                         '<extra></extra>',
            yaxis='y'
        ))
        
        # Add threshold lines
        optimizer_cfg = config.get_optimizer_config()
        cheap_threshold = optimizer_cfg.get('cheap_price_threshold_eur', 3.0)
        expensive_threshold = optimizer_cfg.get('expensive_price_threshold_eur', 8.0)
        
        fig.add_hline(
            y=cheap_threshold,
            line_dash="dash",
            line_color="green",
            annotation_text="Cheap threshold",
            annotation_position="right",
        )
        
        fig.add_hline(
            y=expensive_threshold,
            line_dash="dash",
            line_color="red",
            annotation_text="Expensive threshold",
            annotation_position="right",
        )
        
        # Update layout
        fig.update_layout(
            title="Market Prices (EUR and UAH per MWh)",
            xaxis_title="Hour of Day",
            yaxis=dict(
                title="Price (EUR/MWh)",
                side='left',
                color='#2E86AB',
            ),
            hovermode='x unified',
            height=400,
            showlegend=True,
            template='plotly_white',
        )
        
        st.plotly_chart(fig, width="stretch")
    
    with col_info:
        st.subheader("ℹ️ Price Units")
        st.markdown("""
        **EUR/MWh**
        - European standard
        - Megawatt-Hour
        - 1 MWh = 1,000 kWh
        
        **₴ UAH/MWh**
        - Ukrainian currency
        - ~€1 ≈ ₴35 UAH
        
        **Current Thresholds:**
        """)
        
        optimizer_cfg = config.get_optimizer_config()
        cheap = optimizer_cfg.get('cheap_price_threshold_eur', 3.0)
        expensive = optimizer_cfg.get('expensive_price_threshold_eur', 8.0)
        
        st.success(f"💚 Cheap: <€{cheap:.2f}")
        st.warning(f"🟡 Normal: €{cheap:.2f}-€{expensive:.2f}")
        st.error(f"❤️ Expensive: >€{expensive:.2f}")

st.divider()

# ═══════════════════════════════════════════════════════════════
# OPTIMIZATION RECOMMENDATION
# ═══════════════════════════════════════════════════════════════

if prices_df is not None and len(prices_df) > 0:
    st.subheader("🤖 AI Recommendation")
    
    current_price_eur = prices_df.iloc[current_hour]['price_eur_mwh']
    optimizer_cfg = config.get_optimizer_config()
    cheap_threshold = optimizer_cfg.get('cheap_price_threshold_eur', 3.0)
    expensive_threshold = optimizer_cfg.get('expensive_price_threshold_eur', 8.0)
    
    col_rec1, col_rec2, col_rec3 = st.columns(3)
    
    with col_rec1:
        if current_price_eur < cheap_threshold:
            st.info("""
            💚 **CHARGE FROM GRID**
            
            Current price (€{:.2f}/MWh) is below cheap threshold.
            
            ✅ Actions:
            - Buy from grid
            - Charge battery
            - Store energy for peak hours
            """.format(current_price_eur))
        else:
            st.info("Currently not a good time to charge from grid")
    
    with col_rec2:
        if current_price_eur > expensive_threshold:
            st.error("""
            ❤️ **DISCHARGE TO GRID**
            
            Current price (€{:.2f}/MWh) is above expensive threshold.
            
            ✅ Actions:
            - Sell to grid
            - Discharge battery
            - Maximize revenue
            """.format(current_price_eur))
        else:
            st.info("Currently not a good time to discharge")
    
    with col_rec3:
        if cheap_threshold <= current_price_eur <= expensive_threshold:
            st.warning("""
            🟡 **HOLD / MONITOR**
            
            Current price (€{:.2f}/MWh) is at normal level.
            
            ✅ Actions:
            - Maintain battery level
            - Monitor grid
            - Prepare for changes
            """.format(current_price_eur))
        else:
            st.info("Price is either very cheap or very expensive")

st.divider()

# ═══════════════════════════════════════════════════════════════
# MODEL & RETRAINING INFO
# ═══════════════════════════════════════════════════════════════

st.subheader("🤖 Model Information")

col_model1, col_model2, col_model3 = st.columns(3)

with col_model1:
    st.metric("Model Version", st.session_state.model_version)

with col_model2:
    st.metric("Last Retrained", st.session_state.last_retrain)

with col_model3:
    if st.button("🔄 Retrain Model Now", width="stretch"):
        st.info("Redirecting to Configuration page...")
        st.switch_page("pages/1_configuration.py")

st.divider()

# ═══════════════════════════════════════════════════════════════
# SAMPLE DATA TABLE
# ═══════════════════════════════════════════════════════════════

if prices_df is not None and len(prices_df) > 0:
    st.subheader("📋 Hourly Price Data")
    
    # Create display dataframe with better formatting
    display_df = prices_df.copy()
    display_df['hour'] = display_df['hour'].astype(int).apply(lambda h: f"{h:02d}:00")
    display_df['price_eur_mwh'] = display_df['price_eur_mwh'].apply(lambda p: f"€{p:.2f}")
    display_df['price_uah_mwh'] = display_df['price_uah_mwh'].apply(lambda p: f"₴{p:,.0f}")
    
    display_df = display_df[['hour', 'price_eur_mwh', 'price_uah_mwh']]
    display_df.columns = ['Hour', 'Price (EUR/MWh)', 'Price (₴ UAH/MWh)']
    
    st.dataframe(display_df, width="stretch", height=400)

st.divider()

# ═══════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════

col_footer1, col_footer2, col_footer3 = st.columns(3)

with col_footer1:
    if st.button("⚙️ Go to Configuration"):
        st.switch_page("pages/1_configuration.py")

with col_footer2:
    st.write(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

with col_footer3:
    if st.button("🔄 Refresh Prices"):
        st.cache_data.clear()
        st.rerun()
