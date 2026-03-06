#!/usr/bin/env python3
"""
Smart Energy AI Control System Demo

This script demonstrates the complete two-layer architecture:
1. Control System: Real battery control with VirtualInverterController
2. Physics Simulator: Realistic battery behavior with degradation models
3. User Preferences: Multi-objective optimization
4. Integration: ML pipeline ready

Run this to see the full system in action!
"""

import asyncio
import importlib.util
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add project paths
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Imports
from control.inverter_controller import (
    VirtualInverterController,
    ControlCommand,
    ControlAction,
    ControlMode
)
from simulator.battery_physics import (
    create_battery_model,
    BATTERY_CONFIGS,
    LFPBatteryModel,
    LeadAcidBatteryModel,
    VRFBBatteryModel
)
from optimizer.multi_objective import (
    UserPreferenceEngine,
    ScheduleOptimizer,
    UserPreference
)


def _load_support_module():
    try:
        import demo_complete_system_support as support_module

        return support_module
    except Exception:
        support_path = Path(__file__).with_name("demo_complete_system_support.py")
        module_name = "demo_complete_system_support"
        existing_module = sys.modules.get(module_name)
        if existing_module is not None:
            return existing_module

        spec = importlib.util.spec_from_file_location(module_name, support_path)
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module


_SUPPORT_MODULE = _load_support_module()
demo_custom_scenarios = _SUPPORT_MODULE.demo_custom_scenarios
demo_integration = _SUPPORT_MODULE.demo_integration
demo_physics_simulator = _SUPPORT_MODULE.demo_physics_simulator
demo_user_preferences = _SUPPORT_MODULE.demo_user_preferences
print_command_history = _SUPPORT_MODULE.print_command_history
print_completion_banner = _SUPPORT_MODULE.print_completion_banner
print_intro_banner = _SUPPORT_MODULE.print_intro_banner
print_section = _SUPPORT_MODULE.print_section
print_status = _SUPPORT_MODULE.print_status
run_demo_commands = _SUPPORT_MODULE.run_demo_commands


async def demo_control_system():
    """Demonstrate the control system"""
    print_section("🎮 CONTROL SYSTEM DEMONSTRATION")
    
    # Create controller
    controller = VirtualInverterController(
        battery_capacity_kwh=10.0,
        max_power_kw=5.0,
        initial_soc=0.6  # Start at 60%
    )
    
    print("✅ Virtual Inverter Controller initialized")
    print(f"   Battery: {controller.battery_capacity_kwh}kWh")
    print(f"   Max Power: {controller.max_power_kw}kW") 
    print(f"   Initial SOC: {controller.current_soc*100:.1f}%")
    
    await run_demo_commands(controller, _SUPPORT_MODULE.build_demo_commands(), asyncio.sleep)
    print_command_history(controller)
    
    return controller

async def main():
    """Run complete system demonstration"""
    print_intro_banner()
    
    try:
        # Demo each component
        controller = await demo_control_system()
        physics_models = demo_physics_simulator() 
        demo_user_preferences(controller, physics_models)
        demo_custom_scenarios()
        demo_integration()
        print_completion_banner()
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(result)
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
        sys.exit(0)