"""
Streamlit Configuration & Training Dashboard
Manage system constants and trigger retraining at runtime
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime
import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import get_config, SystemConfig
from src.train_baseline import train_baseline_with_real_data
import logging

logger = logging.getLogger(__name__)

# Configure Streamlit page
st.set_page_config(
    page_title="Smart Energy - Configuration",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("⚙️ Smart Energy System - Configuration & Training")
st.markdown("---")

# Get config
config = get_config()

# Sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Select Page",
    ["📊 Current Configuration", "✏️ Edit Configuration", "🤖 Train Model", "📈 Training Results"]
)

# Page 1: Current Configuration
if page == "📊 Current Configuration":
    st.header("Current System Configuration")
    st.markdown("All constants used in training and optimization")
    
    # Display config summary
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Create tabs for each section
        tabs = st.tabs(["Battery", "Solar", "Grid", "Diesel", "Training", "Optimizer"])
        
        with tabs[0]:  # Battery
            battery = config.get_battery_config()
            st.subheader("🔋 Battery Specifications")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Capacity", f"{battery.get('capacity_kwh', 150)} kWh")
                st.metric("Charge Efficiency", f"{battery.get('charge_efficiency', 0.95)*100:.1f}%")
            with col2:
                st.metric("Min SOC", f"{battery.get('min_soc_percent', 10)}%")
                st.metric("Max SOC", f"{battery.get('max_soc_percent', 95)}%")
            
            with st.expander("Full Battery Config"):
                st.json(battery)
        
        with tabs[1]:  # Solar
            solar = config.get_solar_config()
            st.subheader("☀️ Solar Specifications")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Installed Capacity", f"{solar.get('installed_capacity_kw', 20)} kW")
                st.metric("Panel Efficiency", f"{solar.get('panel_efficiency', 0.20)*100:.1f}%")
            with col2:
                st.metric("Inverter Efficiency", f"{solar.get('inverter_efficiency', 0.95)*100:.1f}%")
            
            with st.expander("Full Solar Config"):
                st.json(solar)
        
        with tabs[2]:  # Grid
            grid = config.get_grid_config()
            st.subheader("🔌 Grid Specifications")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Max Import Power", f"{grid.get('max_import_power_kw', 100)} kW")
            with col2:
                st.metric("Max Export Power", f"{grid.get('max_export_power_kw', 50)} kW")
            
            with st.expander("Full Grid Config"):
                st.json(grid)
        
        with tabs[3]:  # Diesel
            diesel = config.config.get('diesel_generator', {})
            st.subheader("⛽ Diesel Generator (Backup)")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Capacity", f"{diesel.get('capacity_kw', 50)} kW")
            with col2:
                st.metric("Fuel Cost", f"{diesel.get('fuel_cost_eur_per_kwh', 0.25):.2f} €/kWh")
            
            with st.expander("Full Diesel Config"):
                st.json(diesel)
        
        with tabs[4]:  # Training
            training = config.get_training_config()
            st.subheader("🤖 Training Parameters")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Learning Rate", f"{training.get('learning_rate', 0.0003)}")
                st.metric("Gamma", f"{training.get('gamma', 0.99)}")
            with col2:
                st.metric("Batch Size", training.get('batch_size', 64))
                st.metric("Episodes", training.get('episodes', 100))
            
            with st.expander("Full Training Config"):
                st.json(training)
        
        with tabs[5]:  # Optimizer
            optimizer = config.get_optimizer_config()
            st.subheader("⚡ Optimizer Thresholds")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Cheap Price", f"{optimizer.get('cheap_price_threshold_eur', 3.0):.2f} €/MWh")
                st.metric("Low Battery", f"{optimizer.get('low_battery_threshold', 0.2)*100:.0f}%")
            with col2:
                st.metric("Expensive Price", f"{optimizer.get('expensive_price_threshold_eur', 8.0):.2f} €/MWh")
                st.metric("High Battery", f"{optimizer.get('high_battery_threshold', 0.9)*100:.0f}%")
            
            with st.expander("Full Optimizer Config"):
                st.json(optimizer)
    
    with col2:
        st.subheader("⚡ Quick Actions")
        
        # Reset button
        if st.button("🔄 Reset to Defaults", key="reset_btn"):
            config.reset_to_defaults()
            st.success("✅ Reset to defaults!")
            st.rerun()
        
        # Download config
        config_json = json.dumps(config.to_dict(), indent=2)
        st.download_button(
            label="📥 Download Config",
            data=config_json,
            file_name=f"system_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )

# Page 2: Edit Configuration
elif page == "✏️ Edit Configuration":
    st.header("Edit System Configuration")
    st.markdown("Modify any constant and save. Changes will be used in next training run.")
    
    with st.form("config_form"):
        st.subheader("📝 Battery Settings")
        col1, col2 = st.columns(2)
        with col1:
            battery_capacity = st.number_input(
                "Battery Capacity (kWh)",
                min_value=10, max_value=1000,
                value=config.get('battery.capacity_kwh', 150),
                step=10
            )
            battery_min_soc = st.slider(
                "Minimum SOC (%)",
                min_value=0, max_value=50,
                value=int(config.get('battery.min_soc_percent', 10)),
                step=5
            )
        with col2:
            battery_charge_eff = st.slider(
                "Charge Efficiency",
                min_value=0.8, max_value=1.0,
                value=config.get('battery.charge_efficiency', 0.95),
                step=0.01
            )
            battery_max_soc = st.slider(
                "Maximum SOC (%)",
                min_value=50, max_value=100,
                value=int(config.get('battery.max_soc_percent', 95)),
                step=5
            )
        
        st.divider()
        st.subheader("☀️ Solar Settings")
        col1, col2 = st.columns(2)
        with col1:
            solar_capacity = st.number_input(
                "Solar Installed Capacity (kW)",
                min_value=1, max_value=500,
                value=config.get('solar.installed_capacity_kw', 20),
                step=5
            )
            solar_panel_eff = st.slider(
                "Panel Efficiency",
                min_value=0.10, max_value=0.25,
                value=config.get('solar.panel_efficiency', 0.20),
                step=0.01
            )
        with col2:
            solar_inverter_eff = st.slider(
                "Inverter Efficiency",
                min_value=0.90, max_value=0.99,
                value=config.get('solar.inverter_efficiency', 0.95),
                step=0.01
            )
        
        st.divider()
        st.subheader("🔌 Grid Settings")
        col1, col2 = st.columns(2)
        with col1:
            grid_import = st.number_input(
                "Max Import Power (kW)",
                min_value=10, max_value=500,
                value=config.get('grid.max_import_power_kw', 100),
                step=10
            )
        with col2:
            grid_export = st.number_input(
                "Max Export Power (kW)",
                min_value=10, max_value=500,
                value=config.get('grid.max_export_power_kw', 50),
                step=10
            )
        
        st.divider()
        st.subheader("⚡ Optimizer Thresholds")
        col1, col2 = st.columns(2)
        with col1:
            cheap_threshold = st.number_input(
                "Cheap Price Threshold (€/MWh)",
                min_value=0.0, max_value=10.0,
                value=config.get('optimizer.cheap_price_threshold_eur', 3.0),
                step=0.5
            )
            low_battery = st.slider(
                "Low Battery Threshold (%)",
                min_value=0, max_value=50,
                value=int(config.get('optimizer.low_battery_threshold', 0.2)*100),
                step=5
            )
        with col2:
            expensive_threshold = st.number_input(
                "Expensive Price Threshold (€/MWh)",
                min_value=5.0, max_value=20.0,
                value=config.get('optimizer.expensive_price_threshold_eur', 8.0),
                step=0.5
            )
            high_battery = st.slider(
                "High Battery Threshold (%)",
                min_value=50, max_value=100,
                value=int(config.get('optimizer.high_battery_threshold', 0.9)*100),
                step=5
            )
        
        st.divider()
        
        # Submit button
        submitted = st.form_submit_button("💾 Save Configuration", use_container_width=True)
        
        if submitted:
            # Update all values
            config.set('battery.capacity_kwh', battery_capacity)
            config.set('battery.min_soc_percent', battery_min_soc)
            config.set('battery.charge_efficiency', battery_charge_eff)
            config.set('battery.max_soc_percent', battery_max_soc)
            
            config.set('solar.installed_capacity_kw', solar_capacity)
            config.set('solar.panel_efficiency', solar_panel_eff)
            config.set('solar.inverter_efficiency', solar_inverter_eff)
            
            config.set('grid.max_import_power_kw', grid_import)
            config.set('grid.max_export_power_kw', grid_export)
            
            config.set('optimizer.cheap_price_threshold_eur', cheap_threshold)
            config.set('optimizer.expensive_price_threshold_eur', expensive_threshold)
            config.set('optimizer.low_battery_threshold', low_battery / 100)
            config.set('optimizer.high_battery_threshold', high_battery / 100)
            
            config.save_config()
            
            st.success("✅ Configuration saved successfully!")
            st.info("⚠️ Changes will be used in the next training run. Click 'Train Model' to retrain.")

# Page 3: Train Model
elif page == "🤖 Train Model":
    st.header("Train Baseline Model")
    st.markdown("Train a new baseline model with current configuration")
    
    # Show current config being used
    with st.expander("📋 Current Configuration", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Battery", f"{config.get('battery.capacity_kwh')} kWh")
            st.metric("Solar", f"{config.get('solar.installed_capacity_kw')} kW")
        with col2:
            st.metric("Grid Import", f"{config.get('grid.max_import_power_kw')} kW")
            st.metric("Cheap Threshold", f"{config.get('optimizer.cheap_price_threshold_eur'):.2f} €")
        with col3:
            st.metric("Config File", "config/system_config.json")
    
    st.divider()
    
    # Training controls
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🚀 Start Training")
        st.markdown("""
        This will:
        1. Fetch REAL price data from OREE
        2. Train a baseline Random Forest model
        3. Evaluate performance
        4. Save results
        """)
    
    with col2:
        st.subheader("📊 Training Info")
        training_config = config.get_training_config()
        st.info(f"""
        **Configuration:**
        - Learning Rate: {training_config.get('learning_rate')}
        - Episodes: {training_config.get('episodes')}
        - Batch Size: {training_config.get('batch_size')}
        """)
    
    st.divider()
    
    # Train button
    if st.button("▶️ START TRAINING", key="train_btn", use_container_width=True):
        st.markdown("---")
        
        # Show progress
        progress_bar = st.progress(0)
        status_text = st.empty()
        output_box = st.empty()
        
        try:
            status_text.info("🔄 Starting training with current configuration...")
            
            # Redirect logging to display
            import io
            log_capture = io.StringIO()
            handler = logging.StreamHandler(log_capture)
            logger.addHandler(handler)
            
            # Run training
            progress_bar.progress(25)
            status_text.info("⏳ Fetching real price data...")
            
            # Call training function
            train_baseline_with_real_data()
            
            progress_bar.progress(100)
            status_text.success("✅ Training completed successfully!")
            
            # Show output
            output = log_capture.getvalue()
            if output:
                with output_box.container():
                    st.text_area("Training Output", output, height=200, disabled=True)
            
            # Save training metadata
            training_metadata = {
                "timestamp": datetime.now().isoformat(),
                "configuration": config.to_dict(),
                "status": "success"
            }
            
            with open("config/last_training.json", "w") as f:
                json.dump(training_metadata, f, indent=2)
            
            st.success("💾 Training metadata saved!")
            
        except Exception as e:
            progress_bar.progress(0)
            status_text.error(f"❌ Training failed: {str(e)}")
            st.exception(e)

# Page 4: Training Results
elif page == "📈 Training Results":
    st.header("Training Results")
    st.markdown("Results from the last training run")
    
    try:
        with open("config/last_training.json", "r") as f:
            last_training = json.load(f)
        
        col1, col2 = st.columns(2)
        with col1:
            st.success(f"✅ Status: {last_training.get('status', 'unknown').upper()}")
            st.info(f"📅 Timestamp: {last_training.get('timestamp', 'unknown')}")
        
        with col2:
            # Show config used
            config_used = last_training.get('configuration', {})
            battery = config_used.get('battery', {})
            st.metric("Battery (Used)", f"{battery.get('capacity_kwh', '?')} kWh")
        
        st.divider()
        st.subheader("⚙️ Configuration Used")
        st.json(config_used)
        
    except FileNotFoundError:
        st.warning("⚠️ No training results found. Please run training first.")
    except Exception as e:
        st.error(f"Error loading results: {str(e)}")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: gray; font-size: 0.8em;">
    Smart Energy Configuration Dashboard | Configuration stored in config/system_config.json
</div>
""", unsafe_allow_html=True)
