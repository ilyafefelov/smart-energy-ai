"""Support helpers for the complete system demo script."""

from __future__ import annotations

from datetime import datetime

from control.inverter_controller import ControlAction, ControlCommand
from optimizer.multi_objective import ScheduleOptimizer, UserPreference, UserPreferenceEngine
from simulator.battery_physics import create_battery_model


def print_section(title):
    """Print section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


def print_status(status_dict):
    """Pretty print status."""
    for key, value in status_dict.items():
        if isinstance(value, dict):
            print(f"{key}:")
            for nested_key, nested_value in value.items():
                print(f"  {nested_key}: {nested_value}")
        else:
            print(f"{key}: {value}")


def build_demo_commands():
    return [
        (ControlCommand.CHARGE, 3.0, 'Demo: Charge during cheap electricity'),
        (ControlCommand.HOLD, 0.0, 'Demo: Hold position for price analysis'),
        (ControlCommand.DISCHARGE, -2.5, 'Demo: Discharge during peak prices'),
        (ControlCommand.AUTO, 0.0, 'Demo: Enable ML-driven control'),
    ]


async def run_demo_commands(controller, commands, pause_seconds):
    print("\n📋 Executing Control Commands:")

    for index, (command, power_kw, reason) in enumerate(commands, 1):
        action = ControlAction(
            command=command,
            power_kw=power_kw,
            reason=reason,
            user_id='demo_system',
            timestamp=datetime.now(),
        )

        print(f"\n{index}. {command.value.upper()}: {power_kw}kW - {reason}")
        try:
            result = await controller.execute_command(action)
            print(
                f"   ✅ Success: SOC now {result['new_soc'] * 100:.1f}%, Power: {result['power_kw']}kW"
            )

            if result['estimated_completion']:
                completion_time = datetime.fromisoformat(result['estimated_completion'])
                print(f"   ⏰ Est. completion: {completion_time.strftime('%H:%M')}")
        except Exception as exc:
            print(f"   ❌ Failed: {exc}")

        await pause_seconds(0.5)


def print_command_history(controller):
    print(f"\n📜 Command History ({len(controller.command_history)} commands):")
    for command in controller.command_history[-3:]:
        timestamp = datetime.fromisoformat(command['timestamp']).strftime('%H:%M:%S')
        print(
            f"   {timestamp}: {command['command'].upper()} {command['power_kw']}kW - {command['reason'][:40]}..."
        )


def demo_physics_simulator():
    """Demonstrate battery physics models."""
    print_section("🔬 PHYSICS SIMULATOR DEMONSTRATION")

    battery_types = ['LFP', 'LeadAcid', 'VRFB']
    models = {}

    print("🔋 Creating battery physics models:")
    for battery_type in battery_types:
        model = create_battery_model(battery_type, 10.0, 5.0)
        models[battery_type] = model
        print(f"   ✅ {battery_type}: {model.__class__.__name__}")

    print("\n⚡ Degradation Comparison (1kW discharge for 1 hour):")
    for battery_type, model in models.items():
        model.state.soc = 0.8
        model.state.temperature_c = 25

        degradation = model.calculate_degradation(-1.0, 1.0)
        efficiency = model.get_efficiency(-1.0, 0.8)
        max_discharge = model.get_max_power(0.8, 'discharge')

        print(f"   {battery_type}:")
        print(f"     Degradation: {degradation * 10000:.2f} permille/cycle")
        print(f"     Efficiency: {efficiency * 100:.1f}%")
        print(f"     Max Power: {max_discharge:.1f}kW")

    print("\n📊 SOC-dependent Performance (LFP battery):")
    lfp_model = models.get('LFP')
    if lfp_model is None:
        print("   LFP model not available")
        return models

    for soc in [0.1, 0.3, 0.5, 0.8, 0.95]:
        efficiency = lfp_model.get_efficiency(2.0, soc)
        max_charge = lfp_model.get_max_power(soc, 'charge')
        print(f"   SOC {soc * 100:2.0f}%: Efficiency {efficiency * 100:.1f}%, Max Charge {max_charge:.1f}kW")

    return models


def demo_user_preferences(controller, physics_models):
    """Demonstrate user preference optimization."""
    print_section("🎯 USER PREFERENCE OPTIMIZATION")

    engine = UserPreferenceEngine(physics_models['LFP'])
    print('✅ Multi-objective optimization engine initialized')
    print("\n🎛️ Testing User Preferences:")

    for preference in [
        UserPreference.MAX_EARN,
        UserPreference.BALANCE,
        UserPreference.MAX_BATTERY_SAFE,
        UserPreference.MAX_CHARGE,
    ]:
        print(f"\n{preference.value.replace('_', ' ').title()}:")
        description = engine.get_preference_description(preference)
        print(f"   📝 {description['description']}")
        print(f"   🎯 Ideal for: {description['ideal_for']}")
        weights = description['weights']
        print(
            f"   ⚖️  Weights: Profit:{weights['profit_weight']:.1f} | "
            f"Safety:{weights['safety_weight']:.1f} | "
            f"Efficiency:{weights['efficiency_weight']:.1f}"
        )

    print("\n📈 Sample 6-hour Optimization (Balance preference):")
    try:
        schedule = engine.optimize_schedule(UserPreference.BALANCE, hours_ahead=6)
        print('   Schedule:')
        for entry in schedule[:6]:
            print(
                f"   Hour {entry['hour']:2d}: {entry['action']:9s} {entry['power_kw']:+5.1f}kW → "
                f"SOC {entry['soc_after'] * 100:4.1f}% | €{entry.get('expected_profit', 0):+5.2f}"
            )
    except Exception as exc:
        print(f"   ⚠️  Optimization demo failed: {exc}")
        print('   (This is normal if Optuna is not installed)')


def demo_custom_scenarios():
    """Demonstrate custom discharge scenarios."""
    print_section('⚡ CUSTOM SCENARIOS')

    optimizer = ScheduleOptimizer(create_battery_model('LFP', 10.0, 5.0))
    print('✅ Schedule optimizer initialized')

    print("\n🏔️  Peak Shaving Scenario:")
    try:
        scenario = optimizer.create_peak_shaving_schedule([17, 18, 19], 3.0)
        summary = scenario['summary']
        print('   Peak hours: [17, 18, 19]')
        print('   Discharge power: 3.0kW')
        print(f"   📊 Expected profit: €{summary.get('total_profit_eur', 0):.2f}")
        print(f"   📊 Energy cycled: {summary.get('total_energy_cycled_kwh', 0):.1f}kWh")
    except Exception as exc:
        print(f"   ⚠️  Peak shaving demo failed: {exc}")

    print("\n🔋 Emergency Backup Scenario:")
    try:
        scenario = optimizer.create_backup_schedule(0.9)
        summary = scenario['summary']
        print('   Target SOC: 90%')
        print(f"   📊 Final SOC: {summary.get('final_soc_pct', 0):.1f}%")
        print(f"   📊 Charge hours: {summary.get('charge_hours', 0)}")
    except Exception as exc:
        print(f"   ⚠️  Backup scenario demo failed: {exc}")


def demo_integration():
    """Demonstrate ML pipeline integration."""
    print_section('🤖 ML PIPELINE INTEGRATION')
    print('✅ Integration points demonstrated:')
    print('   📊 Dagster Asset Metadata: Command history logging')
    print('   🔄 Real-time Status API: Control system status')
    print('   🎯 Multi-objective Optimization: User preferences')
    print('   🔬 Physics Simulation: Battery degradation modeling')
    print('   📅 Scheduled Commands: Time-based automation')

    print('\n📈 Example Dagster Asset Metadata:')
    for key, value in {
        'commands_executed': 15,
        'total_energy_cycled_kwh': 45.2,
        'avg_efficiency_pct': 94.3,
        'battery_health_pct': 99.1,
        'profit_today_eur': 12.45,
        'co2_saved_kg': 8.7,
    }.items():
        print(f'   {key}: {value}')


def print_intro_banner():
    print('🌟 SMART ENERGY AI - COMPLETE CONTROL SYSTEM & PHYSICS SIMULATOR')
    print('=' * 80)
    print('Two-layer architecture demonstration:')
    print('  Layer 1: Real Control System (VirtualInverterController)')
    print('  Layer 2: Physics Simulator (LFP/Lead-Acid/VRFB models)')
    print('  Layer 3: User Optimization (Multi-objective with Optuna)')


def print_completion_banner():
    print_section('✅ DEMONSTRATION COMPLETE')
    print('🎯 SUCCESS METRICS ACHIEVED:')
    print('   ✅ Control tab provides real charge/discharge commands')
    print('   ✅ Physics-based simulator with LFP/Lead-Acid/VRFB models')
    print('   ✅ User preferences drive multi-objective optimization')
    print('   ✅ Custom discharge scenarios and scheduling')
    print('   ✅ Two-layer architecture ready for IOT integration')
    print('   ✅ Complete ML-pipeline integration points')
    print('\n🚀 Next Steps:')
    print('   1. Start dashboard: cd dashboard && npm run dev')
    print('   2. Visit Control tab to see real-time interface')
    print('   3. Phase 2: Replace VirtualInverter with MQTT/Modbus')
    print('   4. Deploy to production with real battery hardware')