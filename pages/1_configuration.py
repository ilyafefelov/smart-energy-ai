"""
Enhanced Configuration Page with RL Model Retraining
Settings, User Profiles, Retraining Controls, and Solar Config
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os
import sys
import time

# Add project root
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from src.enhanced_config import get_config, UserProfile
from src.enhanced_rl_trainer import EnhancedRLTrainer

# Configure page
st.set_page_config(page_title="System Configuration", layout="wide", initial_sidebar_state="expanded")

# Initialize session state
if 'retrain_status' not in st.session_state:
    st.session_state.retrain_status = "idle"
if 'retrain_progress' not in st.session_state:
    st.session_state.retrain_progress = 0
if 'retrain_result' not in st.session_state:
    st.session_state.retrain_result = None

# ═══════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════

st.title("⚙️ System Configuration & Control")
st.markdown("Manage settings, profiles, retraining, and system updates")

config = get_config()

# Tab navigation
tabs = st.tabs([
    "👤 Profiles",
    "🔧 Hardware",
    "🤖 Retraining",
    "☀️ Solar",
    "📊 Optimizer",
    "📈 Version History"
])

# ═══════════════════════════════════════════════════════════════
# TAB 1: USER PROFILES
# ═══════════════════════════════════════════════════════════════

with tabs[0]:
    st.subheader("👤 User Profiles")
    st.markdown("Create and manage system user profiles with different configurations")
    
    st.divider()
    
    # Create new profile section
    with st.expander("➕ Create New Profile", open=False):
        col_name, col_desc = st.columns(2)
        
        with col_name:
            profile_name = st.text_input("Profile Name", placeholder="e.g., residential_small")
        
        with col_desc:
            profile_desc = st.text_input("Description", placeholder="e.g., Small residential system")
        
        if st.button("Create Profile"):
            if profile_name and profile_desc:
                try:
                    profile = config.create_profile(
                        name=profile_name,
                        description=profile_desc
                    )
                    st.success(f"✅ Created profile: {profile_name}")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
            else:
                st.warning("⚠️ Please fill in all fields")
    
    st.divider()
    
    # List existing profiles
    st.subheader("Available Profiles")
    
    profiles = config.list_profiles()
    
    if profiles:
        for profile_name in profiles:
            with st.expander(f"📋 {profile_name}", open=False):
                try:
                    profile = config.load_profile(profile_name)
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**Battery System**")
                        st.text(f"Capacity: {profile.battery_capacity_kwh} kWh")
                        st.text(f"SOC Range: {profile.battery_min_soc_percent}% - {profile.battery_max_soc_percent}%")
                        st.text(f"Charge Eff: {profile.battery_charge_efficiency*100:.0f}%")
                    
                    with col2:
                        st.write("**Solar System**")
                        st.text(f"Capacity: {profile.solar_capacity_kw} kW")
                        st.text(f"Panel Eff: {profile.solar_panel_efficiency*100:.0f}%")
                        st.text(f"Inverter: {profile.solar_inverter_efficiency*100:.0f}%")
                    
                    if st.button(f"Delete {profile_name}"):
                        config.delete_profile(profile_name)
                        st.rerun()
                
                except Exception as e:
                    st.error(f"Error loading profile: {e}")
    else:
        st.info("No profiles created yet. Create one above!")
    
    # Default profiles
    if st.button("🔄 Create Default Profiles"):
        config.create_default_profiles()
        st.success("✅ Created 3 example profiles")
        st.rerun()

# ═══════════════════════════════════════════════════════════════
# TAB 2: HARDWARE SETTINGS
# ═══════════════════════════════════════════════════════════════

with tabs[1]:
    st.subheader("🔧 Hardware Configuration")
    st.markdown("Edit battery, grid, and generator settings")
    
    st.divider()
    
    battery_cfg = config.get_battery_config()
    
    st.write("**Battery System**")
    col_b1, col_b2 = st.columns(2)
    
    with col_b1:
        st.number_input(
            "Battery Capacity (kWh)",
            value=battery_cfg.get('capacity_kwh', 150),
            min_value=10.0,
            max_value=1000.0,
            step=10.0,
            key="battery_capacity",
            disabled=True,
            help="Set via User Profile"
        )
    
    with col_b2:
        st.slider(
            "Min SOC (%)",
            min_value=5,
            max_value=30,
            value=int(battery_cfg.get('min_soc', 0.1) * 100),
            key="battery_min_soc",
            disabled=True,
            help="Set via User Profile"
        )
    
    st.divider()
    
    grid_cfg = config.get_grid_config()
    
    st.write("**Grid Connection**")
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        st.number_input(
            "Max Import (kW)",
            value=grid_cfg.get('max_import_power_kw', 100),
            disabled=True,
            help="Set via User Profile"
        )
    
    with col_g2:
        st.number_input(
            "Max Export (kW)",
            value=grid_cfg.get('max_export_power_kw', 50),
            disabled=True,
            help="Set via User Profile"
        )
    
    st.info("💡 Modify hardware settings by editing user profiles")

# ═══════════════════════════════════════════════════════════════
# TAB 3: RETRAINING (NEW & ENHANCED)
# ═══════════════════════════════════════════════════════════════

with tabs[2]:
    st.subheader("🤖 RL Model Retraining")
    st.markdown("Train and retrain the RL agent for energy optimization")
    
    st.divider()
    
    # Current version info
    col_current, col_control = st.columns([2, 1])
    
    with col_current:
        current_version = config.get_current_version()
        st.metric("Current Model Version", current_version)
        
        history = config.get_version_history()
        if history:
            latest = history[0]
            st.caption(f"Last trained: {latest.trained_at}")
            st.caption(f"Last avg reward: {latest.avg_reward:.2f}")
    
    st.divider()
    
    # Training configuration
    st.subheader("⚙️ Training Configuration")
    
    col_ep, col_lr = st.columns(2)
    
    with col_ep:
        episodes = st.slider(
            "Number of Episodes",
            min_value=10,
            max_value=500,
            value=50,
            step=10,
            help="More episodes = better performance but longer training"
        )
    
    with col_lr:
        lr_options = [1e-4, 3e-4, 1e-3, 3e-3]
        lr = st.selectbox(
            "Learning Rate",
            lr_options,
            index=1,  # Default to 3e-4
            format_func=lambda x: f"{x:.0e}"
        )
    
    st.divider()
    
    # Training button & progress
    st.subheader("🚀 Start Training")
    
    train_button = st.button("▶️ START TRAINING", key="train_button", use_container_width=True)
    
    if train_button:
        st.session_state.retrain_status = "running"
        st.session_state.retrain_progress = 0
    
    # Show progress if training
    if st.session_state.retrain_status == "running":
        progress_container = st.container()
        status_container = st.container()
        
        # Simulate training
        try:
            # Import data
            import pandas as pd
            import numpy as np
            
            # Create synthetic data for training
            hours = 168
            dates = pd.date_range('2025-01-20', periods=hours, freq='h')
            
            weather_data = pd.DataFrame({
                'temp': 5 + 5*np.sin(np.linspace(0, 7*np.pi, hours)) + np.random.normal(0, 2, hours),
                'radiation': np.maximum(0, 500 * np.sin(np.linspace(0, 7*np.pi, hours))),
                'clouds': np.maximum(0, np.minimum(100, 50 + 30*np.sin(np.linspace(0, 7*np.pi, hours)))),
                'wind': np.maximum(0, 10 + 5*np.sin(np.linspace(0, 7*np.pi, hours))),
                'humidity': 60 + 20*np.sin(np.linspace(0, 7*np.pi, hours)),
            }, index=dates)
            
            price_data = pd.DataFrame({
                'price_normalized_minmax': np.random.uniform(0.3, 1.0, hours),
                'price_uah_original': np.random.uniform(100, 500, hours),
            }, index=dates)
            
            # Progress callback
            progress_bar = progress_container.progress(0)
            status_text = status_container.empty()
            
            def progress_callback(pct):
                progress_bar.progress(int(pct) / 100)
                status_text.write(f"Training: {int(pct)}% complete ({int(pct/100 * episodes)} episodes)")
            
            # Train
            trainer = EnhancedRLTrainer(weather_data, price_data, config=config, verbose=False)
            result = trainer.train(episodes=episodes, learning_rate=lr, progress_callback=progress_callback)
            
            st.session_state.retrain_status = "complete"
            st.session_state.retrain_result = result
            
        except Exception as e:
            st.session_state.retrain_status = "error"
            st.error(f"❌ Training error: {str(e)}")
    
    # Show results if complete
    if st.session_state.retrain_status == "complete" and st.session_state.retrain_result:
        result = st.session_state.retrain_result
        
        st.divider()
        st.success("✅ Training Complete!")
        
        col_r1, col_r2, col_r3, col_r4 = st.columns(4)
        
        with col_r1:
            st.metric("New Version", result['version'])
        
        with col_r2:
            st.metric("Episodes", result['episodes'])
        
        with col_r3:
            st.metric("Avg Reward", f"{result['avg_reward']:.2f}")
        
        with col_r4:
            st.metric("Time", f"{result['training_time_seconds']:.1f}s")
        
        st.info(f"Model saved to: {result['model_path'].split(os.sep)[-1]}")
        
        if st.button("✨ Start New Training", key="new_train"):
            st.session_state.retrain_status = "idle"
            st.session_state.retrain_result = None
            st.rerun()

# ═══════════════════════════════════════════════════════════════
# TAB 4: SOLAR CONFIGURATION
# ═══════════════════════════════════════════════════════════════

with tabs[3]:
    st.subheader("☀️ Solar System Configuration")
    st.markdown("Configure solar panels and generation settings")
    
    st.divider()
    
    solar_cfg = config.get_solar_config()
    
    st.write("**Solar Panel Settings**")
    col_s1, col_s2, col_s3 = st.columns(3)
    
    with col_s1:
        st.number_input(
            "Solar Capacity (kW)",
            value=solar_cfg.get('capacity_kw', 20.0),
            min_value=1.0,
            max_value=500.0,
            step=5.0,
            key="solar_capacity",
            disabled=True,
            help="Set via User Profile"
        )
    
    with col_s2:
        st.slider(
            "Panel Efficiency (%)",
            min_value=15,
            max_value=25,
            value=int(solar_cfg.get('panel_efficiency', 0.20) * 100),
            key="solar_efficiency",
            disabled=True,
            help="Set via User Profile"
        )
    
    with col_s3:
        st.slider(
            "Inverter Efficiency (%)",
            min_value=90,
            max_value=98,
            value=int(solar_cfg.get('inverter_efficiency', 0.95) * 100),
            key="inverter_efficiency",
            disabled=True,
            help="Set via User Profile"
        )
    
    st.divider()
    
    st.write("**Solar Data**")
    
    col_loc1, col_loc2 = st.columns(2)
    
    with col_loc1:
        st.text_input(
            "Location",
            value="Kyiv, Ukraine",
            disabled=True
        )
    
    with col_loc2:
        st.text_input(
            "Coordinates",
            value="50.45°N, 30.52°E",
            disabled=True
        )
    
    st.info("💡 Solar data is automatically fetched from OpenWeatherMap API")

# ═══════════════════════════════════════════════════════════════
# TAB 5: OPTIMIZER SETTINGS
# ═══════════════════════════════════════════════════════════════

with tabs[4]:
    st.subheader("📊 Optimizer Thresholds")
    st.markdown("Configure energy optimization parameters")
    
    st.divider()
    
    optimizer_cfg = config.get_optimizer_config()
    
    st.write("**Price Thresholds**")
    col_o1, col_o2 = st.columns(2)
    
    with col_o1:
        st.number_input(
            "Cheap Price Threshold (EUR/MWh)",
            value=optimizer_cfg.get('cheap_price_threshold_eur', 3.0),
            min_value=0.0,
            max_value=20.0,
            step=0.5,
            key="cheap_threshold",
            help="Buy/charge below this price"
        )
    
    with col_o2:
        st.number_input(
            "Expensive Price Threshold (EUR/MWh)",
            value=optimizer_cfg.get('expensive_price_threshold_eur', 8.0),
            min_value=0.0,
            max_value=50.0,
            step=1.0,
            key="expensive_threshold",
            help="Sell/discharge above this price"
        )
    
    st.divider()
    
    st.write("**Battery Thresholds**")
    col_b1, col_b2 = st.columns(2)
    
    with col_b1:
        st.slider(
            "Low Battery Threshold",
            min_value=0.1,
            max_value=0.5,
            value=optimizer_cfg.get('low_battery_threshold', 0.2),
            step=0.05,
            key="low_batt",
            format="%.1f"
        )
    
    with col_b2:
        st.slider(
            "High Battery Threshold",
            min_value=0.7,
            max_value=1.0,
            value=optimizer_cfg.get('high_battery_threshold', 0.9),
            step=0.05,
            key="high_batt",
            format="%.1f"
        )

# ═══════════════════════════════════════════════════════════════
# TAB 6: VERSION HISTORY
# ═══════════════════════════════════════════════════════════════

with tabs[5]:
    st.subheader("📈 Model Version History")
    st.markdown("View all trained model versions and metrics")
    
    st.divider()
    
    history = config.get_version_history()
    
    if history:
        # Create summary table
        summary_data = []
        for ver in history[:10]:  # Show last 10
            summary_data.append({
                'Version': ver.version,
                'Date': ver.trained_at[:10],
                'Episodes': ver.episodes,
                'Avg Reward': f"{ver.avg_reward:.2f}",
                'Best Reward': f"{ver.best_reward:.2f}",
                'Time (s)': f"{ver.training_time_seconds:.1f}"
            })
        
        summary_df = pd.DataFrame(summary_data)
        st.dataframe(summary_df, use_container_width=True)
        
        st.divider()
        
        # Detailed view
        st.write("**Detailed Version Information**")
        
        for ver in history[:5]:
            with st.expander(f"v{ver.version} - {ver.trained_at}"):
                col_d1, col_d2 = st.columns(2)
                
                with col_d1:
                    st.write(f"**Metrics**")
                    st.text(f"Episodes: {ver.episodes}")
                    st.text(f"Avg Reward: {ver.avg_reward:.2f}")
                    st.text(f"Best Reward: {ver.best_reward:.2f}")
                
                with col_d2:
                    st.write(f"**Details**")
                    st.text(f"Training Time: {ver.training_time_seconds:.1f}s")
                    st.text(f"Model Path: {ver.model_path.split(os.sep)[-1]}")
                    if ver.notes:
                        st.text(f"Notes: {ver.notes}")
    else:
        st.info("No training history yet. Start training from the Retraining tab.")

st.divider()

st.caption("Last updated: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
