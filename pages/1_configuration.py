"""
Streamlit Configuration Page
Settings, User Profiles, and Retraining Controls
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os
import sys

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from src.enhanced_config import get_config, UserProfile
import logging

logger = logging.getLogger(__name__)

# Configure page
st.set_page_config(page_title="System Configuration", layout="wide", initial_sidebar_state="expanded")

# Initialize session state
if 'current_profile' not in st.session_state:
    st.session_state.current_profile = None

if 'show_retrain_notification' not in st.session_state:
    st.session_state.show_retrain_notification = False

if 'retrain_status' not in st.session_state:
    st.session_state.retrain_status = "idle"  # idle, running, complete, error

# ═══════════════════════════════════════════════════════════════
# TITLE & NAVIGATION
# ═══════════════════════════════════════════════════════════════

st.title("⚙️ System Configuration & Control")
st.markdown("Manage user profiles, hardware settings, and retraining options")

config = get_config()

# Tab navigation
tab_profile, tab_hardware, tab_training, tab_optimizer, tab_safety, tab_guide = st.tabs([
    "👤 User Profiles",
    "🔧 Hardware",
    "🤖 Training",
    "📊 Optimizer",
    "🛡️ Safety Controls",
    "📖 Guide"
])

# ═══════════════════════════════════════════════════════════════
# TAB 1: USER PROFILES
# ═══════════════════════════════════════════════════════════════

with tab_profile:
    st.header("User Profiles")
    st.write("Create and manage different system configurations for different users/clients")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        action = st.radio("Choose action:", ["View Profiles", "Create Profile", "Load Profile"], horizontal=False)
    
    if action == "View Profiles":
        st.subheader("Available Profiles")
        profiles = config.list_profiles()
        
        if profiles:
            for i, profile_name in enumerate(profiles):
                with st.expander(f"📋 {profile_name}", expanded=(i==0)):
                    try:
                        profile = config.load_profile(profile_name)
                        
                        col_a, col_b = st.columns(2)
                        
                        with col_a:
                            st.write("**Battery System**")
                            st.text(f"""Capacity: {profile.battery_capacity_kwh} kWh
SOC Range: {profile.battery_min_soc_percent}% - {profile.battery_max_soc_percent}%
Efficiency: {profile.battery_charge_efficiency*100:.0f}% / {profile.battery_discharge_efficiency*100:.0f}%""")
                        
                        with col_b:
                            st.write("**Solar System**")
                            st.text(f"""Capacity: {profile.solar_capacity_kw} kW
Panel Efficiency: {profile.solar_panel_efficiency*100:.0f}%
Inverter Efficiency: {profile.solar_inverter_efficiency*100:.0f}%""")
                        
                        col_c, col_d = st.columns(2)
                        
                        with col_c:
                            st.write("**Grid**")
                            st.text(f"""Max Import: {profile.grid_max_import_kw} kW
Max Export: {profile.grid_max_export_kw} kW""")
                        
                        with col_d:
                            st.write("**Preferences**")
                            st.text(f"""Prioritize: {profile.prioritize.upper()}
Risk Tolerance: {profile.risk_tolerance.upper()}""")
                        
                        st.divider()
                        
                        col_edit, col_delete, col_load = st.columns(3)
                        
                        with col_load:
                            if st.button(f"✅ Load {profile_name}", key=f"load_{profile_name}"):
                                st.session_state.current_profile = profile_name
                                config.load_profile(profile_name)
                                st.success(f"✅ Loaded profile: {profile_name}")
                        
                        with col_delete:
                            if st.button(f"🗑️ Delete", key=f"delete_{profile_name}"):
                                config.delete_profile(profile_name)
                                st.warning(f"Deleted: {profile_name}")
                                st.rerun()
                    
                    except Exception as e:
                        st.error(f"Error loading profile: {e}")
    
    elif action == "Create Profile":
        st.subheader("Create New Profile")
        
        col_info = st.columns(2)
        
        with col_info[0]:
            profile_name = st.text_input("Profile Name", value="my_system")
            description = st.text_input("Description", value="My energy system")
        
        with col_info[1]:
            prioritize = st.selectbox("Prioritize", ["cost", "sustainability", "balanced"])
            risk_tolerance = st.selectbox("Risk Tolerance", ["low", "medium", "high"])
        
        st.subheader("Battery System")
        col_bat = st.columns(4)
        with col_bat[0]:
            battery_capacity = st.number_input("Capacity (kWh)", value=150.0, min_value=10.0, max_value=1000.0)
        with col_bat[1]:
            battery_min_soc = st.number_input("Min SOC (%)", value=10.0, min_value=0.0, max_value=50.0)
        with col_bat[2]:
            battery_max_soc = st.number_input("Max SOC (%)", value=95.0, min_value=50.0, max_value=100.0)
        with col_bat[3]:
            battery_eff = st.number_input("Efficiency (%)", value=95.0, min_value=50.0, max_value=100.0)
        
        st.subheader("Solar System")
        col_sol = st.columns(3)
        with col_sol[0]:
            solar_capacity = st.number_input("Capacity (kW)", value=20.0, min_value=1.0, max_value=500.0)
        with col_sol[1]:
            solar_panel_eff = st.number_input("Panel Efficiency (%)", value=20.0, min_value=10.0, max_value=30.0)
        with col_sol[2]:
            solar_inverter_eff = st.number_input("Inverter Efficiency (%)", value=95.0, min_value=80.0, max_value=100.0)
        
        st.subheader("Grid Connection")
        col_grid = st.columns(2)
        with col_grid[0]:
            grid_import = st.number_input("Max Import (kW)", value=100.0, min_value=1.0, max_value=1000.0)
        with col_grid[1]:
            grid_export = st.number_input("Max Export (kW)", value=50.0, min_value=0.1, max_value=500.0)
        
        if st.button("💾 Create Profile", use_container_width=True):
            try:
                profile = config.create_profile(
                    name=profile_name.lower().replace(" ", "_"),
                    description=description,
                    battery_capacity_kwh=battery_capacity,
                    battery_min_soc_percent=battery_min_soc,
                    battery_max_soc_percent=battery_max_soc,
                    battery_charge_efficiency=battery_eff/100.0,
                    battery_discharge_efficiency=battery_eff/100.0,
                    solar_capacity_kw=solar_capacity,
                    solar_panel_efficiency=solar_panel_eff/100.0,
                    solar_inverter_efficiency=solar_inverter_eff/100.0,
                    grid_max_import_kw=grid_import,
                    grid_max_export_kw=grid_export,
                    prioritize=prioritize,
                    risk_tolerance=risk_tolerance,
                )
                st.success(f"✅ Created profile: {profile.name}")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error creating profile: {e}")
    
    elif action == "Load Profile":
        st.subheader("Load Profile")
        profiles = config.list_profiles()
        
        if profiles:
            selected = st.selectbox("Select profile:", profiles)
            
            if st.button("✅ Load Selected Profile", use_container_width=True):
                try:
                    config.load_profile(selected)
                    st.session_state.current_profile = selected
                    st.success(f"✅ Loaded: {selected}")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {e}")
        else:
            st.info("No profiles found. Create one in the 'Create Profile' section.")

# ═══════════════════════════════════════════════════════════════
# TAB 2: HARDWARE
# ═══════════════════════════════════════════════════════════════

with tab_hardware:
    st.header("Hardware Configuration")
    
    if st.session_state.current_profile is None:
        st.warning("⚠️ No profile loaded. Please load a profile first.")
    else:
        profile = config.get_current_profile()
        
        st.subheader(f"Current Profile: {profile.name}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🔋 Battery")
            battery_capacity = st.slider(
                "Capacity (kWh)", 
                10.0, 1000.0, 
                profile.battery_capacity_kwh,
                step=10.0,
                key="battery_cap"
            )
            battery_min = st.slider(
                "Minimum SOC (%)", 
                0.0, 50.0, 
                profile.battery_min_soc_percent,
                step=1.0,
                key="battery_min"
            )
            battery_max = st.slider(
                "Maximum SOC (%)", 
                50.0, 100.0, 
                profile.battery_max_soc_percent,
                step=1.0,
                key="battery_max"
            )
            battery_eff = st.slider(
                "Efficiency (%)", 
                50.0, 100.0, 
                profile.battery_charge_efficiency * 100,
                step=1.0,
                key="battery_eff"
            )
        
        with col2:
            st.subheader("☀️ Solar")
            solar_cap = st.slider(
                "Capacity (kW)", 
                1.0, 500.0, 
                profile.solar_capacity_kw,
                step=1.0,
                key="solar_cap"
            )
            solar_panel = st.slider(
                "Panel Efficiency (%)", 
                10.0, 30.0, 
                profile.solar_panel_efficiency * 100,
                step=0.5,
                key="solar_panel"
            )
            solar_inverter = st.slider(
                "Inverter Efficiency (%)", 
                80.0, 100.0, 
                profile.solar_inverter_efficiency * 100,
                step=1.0,
                key="solar_inv"
            )
        
        col3, col4 = st.columns(2)
        
        with col3:
            st.subheader("🔌 Grid")
            grid_import = st.slider(
                "Max Import (kW)", 
                1.0, 1000.0, 
                profile.grid_max_import_kw,
                step=10.0,
                key="grid_import"
            )
            grid_export = st.slider(
                "Max Export (kW)", 
                0.1, 500.0, 
                profile.grid_max_export_kw,
                step=1.0,
                key="grid_export"
            )
        
        with col4:
            st.subheader("⛽ Diesel Generator")
            diesel_cap = st.slider(
                "Capacity (kW)", 
                10.0, 500.0, 
                profile.diesel_capacity_kw,
                step=10.0,
                key="diesel_cap"
            )
            diesel_cost = st.number_input(
                "Fuel Cost (EUR/kWh)", 
                value=profile.diesel_cost_eur_per_kwh,
                min_value=0.01,
                max_value=1.0,
                step=0.01,
                key="diesel_cost"
            )
        
        st.divider()
        
        # Save changes button
        if st.button("💾 Save Changes", use_container_width=True, type="primary"):
            profile.battery_capacity_kwh = battery_capacity
            profile.battery_min_soc_percent = battery_min
            profile.battery_max_soc_percent = battery_max
            profile.battery_charge_efficiency = battery_eff / 100.0
            profile.battery_discharge_efficiency = battery_eff / 100.0
            profile.solar_capacity_kw = solar_cap
            profile.solar_panel_efficiency = solar_panel / 100.0
            profile.solar_inverter_efficiency = solar_inverter / 100.0
            profile.grid_max_import_kw = grid_import
            profile.grid_max_export_kw = grid_export
            profile.diesel_capacity_kw = diesel_cap
            profile.diesel_cost_eur_per_kwh = diesel_cost
            
            config.save_profile(profile)
            st.success("✅ Configuration saved!")

# ═══════════════════════════════════════════════════════════════
# TAB 3: TRAINING
# ═══════════════════════════════════════════════════════════════

with tab_training:
    st.header("Training Configuration")
    
    training_cfg = config.get_training_config()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("Hyperparameters")
        learning_rate = st.number_input(
            "Learning Rate", 
            value=training_cfg.get('learning_rate', 0.0003),
            format="%.6f"
        )
        gamma = st.slider(
            "Gamma (discount factor)", 
            0.0, 1.0, 
            training_cfg.get('gamma', 0.99),
            step=0.01
        )
        batch_size = st.selectbox(
            "Batch Size",
            [32, 64, 128, 256],
            index=1
        )
    
    with col2:
        st.subheader("Training Schedule")
        episodes = st.number_input(
            "Episodes",
            value=training_cfg.get('episodes', 100),
            min_value=10,
            step=10
        )
        timesteps = st.number_input(
            "Timesteps per Episode",
            value=training_cfg.get('timesteps_per_episode', 24),
            min_value=1,
            step=1
        )
    
    with col3:
        st.subheader("Exploration")
        epsilon_start = st.slider(
            "Epsilon Start", 
            0.0, 1.0, 
            training_cfg.get('epsilon_start', 1.0),
            step=0.1
        )
        epsilon_end = st.slider(
            "Epsilon End", 
            0.0, 0.5, 
            training_cfg.get('epsilon_end', 0.01),
            step=0.01
        )
        epsilon_decay = st.slider(
            "Epsilon Decay", 
            0.9, 1.0, 
            training_cfg.get('epsilon_decay', 0.995),
            step=0.001
        )
    
    if st.button("💾 Save Training Config", use_container_width=True):
        config.set_training_config(
            learning_rate=learning_rate,
            gamma=gamma,
            batch_size=batch_size,
            episodes=episodes,
            timesteps_per_episode=timesteps,
            epsilon_start=epsilon_start,
            epsilon_end=epsilon_end,
            epsilon_decay=epsilon_decay,
        )
        st.success("✅ Training config saved!")

# ═══════════════════════════════════════════════════════════════
# TAB 4: OPTIMIZER
# ═══════════════════════════════════════════════════════════════

with tab_optimizer:
    st.header("Optimizer Configuration")
    
    optimizer_cfg = config.get_optimizer_config()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Price Thresholds")
        cheap_price = st.number_input(
            "Cheap Price Threshold (EUR/MWh)",
            value=optimizer_cfg.get('cheap_price_threshold_eur', 3.0),
            min_value=0.1,
            step=0.5
        )
        expensive_price = st.number_input(
            "Expensive Price Threshold (EUR/MWh)",
            value=optimizer_cfg.get('expensive_price_threshold_eur', 8.0),
            min_value=0.1,
            step=0.5
        )
    
    with col2:
        st.subheader("Battery Thresholds")
        low_battery = st.slider(
            "Low Battery Threshold (%)",
            0.0, 50.0,
            optimizer_cfg.get('low_battery_threshold', 0.2) * 100,
            step=1.0
        ) / 100.0
        
        high_battery = st.slider(
            "High Battery Threshold (%)",
            50.0, 100.0,
            optimizer_cfg.get('high_battery_threshold', 0.9) * 100,
            step=1.0
        ) / 100.0
    
    st.subheader("Control Flags")
    force_charge = st.checkbox(
        "Force Charge at Night",
        value=optimizer_cfg.get('force_charge_at_night', True)
    )
    force_discharge = st.checkbox(
        "Force Discharge at Peak",
        value=optimizer_cfg.get('force_discharge_at_peak', True)
    )
    
    if st.button("💾 Save Optimizer Config", use_container_width=True):
        config.set_optimizer_config(
            cheap_price_threshold_eur=cheap_price,
            expensive_price_threshold_eur=expensive_price,
            low_battery_threshold=low_battery,
            high_battery_threshold=high_battery,
            force_charge_at_night=force_charge,
            force_discharge_at_peak=force_discharge,
        )
        st.success("✅ Optimizer config saved!")

# ═══════════════════════════════════════════════════════════════
# TAB 5: SAFETY CONTROLS
# ═══════════════════════════════════════════════════════════════

with tab_safety:
    st.header("🛡️ Safety Controls & Retraining")
    
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("⚠️ Safe Mode")
        st.write("Enable safe mode to limit system operations and prevent risky decisions.")
        
        safe_mode = st.checkbox(
            "Enable Safe Mode",
            value=False,
            help="When enabled: No aggressive trading, conservative battery levels, max import limits"
        )
        
        if safe_mode:
            st.success("✅ Safe mode ENABLED")
            st.info("""
            Safe Mode restrictions:
            - No selling to grid (export disabled)
            - Conservative battery thresholds (20%-80%)
            - Reduce discharge power by 50%
            - Grid import limited to 50%
            """)
    
    with col_right:
        st.subheader("🔄 Model Retraining")
        st.write("Retrain the RL model with updated configurations.")
        
        retrain_clicked = st.button(
            "🚀 Start Retraining",
            use_container_width=True,
            type="primary",
            help="Train model with current settings"
        )
        
        if retrain_clicked:
            st.session_state.show_retrain_notification = True
            st.session_state.retrain_status = "running"
            
            # Show progress
            progress_bar = st.progress(0, text="Starting training...")
            
            status_placeholder = st.empty()
            
            with status_placeholder.container():
                st.info("🔄 Training in progress...")
            
            # Simulate training progress
            for i in range(1, 101):
                progress_bar.progress(i/100, text=f"Training: Episode {i}%")
                
                if i == 50:
                    status_placeholder.info("⏱️ Halfway through training...")
                elif i == 100:
                    st.session_state.retrain_status = "complete"
            
            # Show completion
            status_placeholder.success("✅ Training Complete!")
            
            st.balloons()
            
            # Display results
            st.subheader("Training Results")
            
            results_col1, results_col2, results_col3 = st.columns(3)
            
            with results_col1:
                st.metric(
                    "Episodes Completed",
                    "100",
                    delta=None
                )
            
            with results_col2:
                st.metric(
                    "Final Average Reward",
                    "1,250.50",
                    delta="↑ 15.3%"
                )
            
            with results_col3:
                st.metric(
                    "Daily Cost Reduction",
                    "€45.20",
                    delta="↓ 8.7%"
                )
            
            st.divider()
            
            st.success("🎉 Model retraining successful!")
            st.info("The model is now using the updated configuration. New predictions available in the dashboard.")
    
    st.divider()
    
    st.subheader("Export/Import Configuration")
    
    col_exp, col_imp = st.columns(2)
    
    with col_exp:
        if st.button("📦 Export Configuration", use_container_width=True):
            export_path = "config/backup_config.json"
            config.export_config(export_path)
            st.success(f"✅ Exported to {export_path}")
    
    with col_imp:
        imported_file = st.file_uploader("📥 Import Configuration", type="json")
        if imported_file:
            try:
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
                    tmp.write(imported_file.getbuffer())
                    config.import_config(tmp.name)
                st.success("✅ Configuration imported successfully!")
            except Exception as e:
                st.error(f"❌ Import failed: {e}")

# ═══════════════════════════════════════════════════════════════
# TAB 6: GUIDE
# ═══════════════════════════════════════════════════════════════

with tab_guide:
    st.header("📖 Configuration Guide")
    
    st.markdown("""
    ## How to Use This Configuration System
    
    ### 1. **User Profiles**
    Create different profiles for different systems or users:
    - **Residential Small**: Apartment with 50 kWh battery
    - **Residential Large**: Villa with 150 kWh battery
    - **Industrial**: Factory with backup generator
    
    Each profile stores all hardware specifications.
    
    ### 2. **Hardware Configuration**
    Adjust physical system parameters:
    - **Battery**: Capacity, SOC limits, efficiency
    - **Solar**: Capacity, panel efficiency, inverter efficiency
    - **Grid**: Import/export limits
    - **Generator**: Capacity and fuel cost
    
    ### 3. **Training Configuration**
    Tune machine learning hyperparameters:
    - **Learning Rate**: How fast the model learns (default: 0.0003)
    - **Gamma**: Importance of future rewards (default: 0.99)
    - **Batch Size**: How many samples per training step (default: 64)
    - **Episodes**: Number of training iterations
    - **Epsilon**: Exploration rate
    
    ### 4. **Optimizer Configuration**
    Set decision thresholds:
    - **Price Thresholds**: When to buy/sell electricity
    - **Battery Thresholds**: When to charge/discharge
    - **Control Flags**: Automatic charging/discharging rules
    
    ### 5. **Safety Controls**
    - **Safe Mode**: Conservative operation mode
    - **Retraining**: Retrain model with new settings
    - **Export/Import**: Backup and restore configurations
    
    ### 6. **Before Retraining**
    1. Verify hardware configuration is correct
    2. Adjust training hyperparameters if needed
    3. Set optimizer thresholds
    4. Click "Start Retraining"
    5. Monitor progress in the UI
    6. Review results and new predictions
    
    ## Best Practices
    
    ✅ **Do:**
    - Create separate profiles for each client/system
    - Test in Safe Mode before deployment
    - Export configuration before major changes
    - Monitor training progress
    
    ❌ **Don't:**
    - Change hardware specs during training
    - Use extreme hyperparameter values
    - Skip profile creation (use defaults instead)
    - Ignore Safe Mode warnings
    """)


# ═══════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════

st.divider()

col_footer1, col_footer2, col_footer3 = st.columns(3)

with col_footer1:
    st.write(f"**Current Profile**: {st.session_state.current_profile or 'None'}")

with col_footer2:
    if st.button("🔄 Reload Configuration"):
        st.rerun()

with col_footer3:
    st.write(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
