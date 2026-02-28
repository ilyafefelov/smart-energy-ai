import pytest
from energy_ml.config_models import BatteryConfig, UserProfile, LoadProfileConfig
from energy_ml.battery_degradation import LFPModel, LeadAcidModel, VRFBModel


def make_user(batt_conf):
    profile = UserProfile(
        user_id='test',
        profile_name='test',
        battery=batt_conf,
        load_profile=LoadProfileConfig.create_standard_work_profile(peak_load_kw=10.0),
        generation={},
        tariff={}
    )
    return profile


def test_lfp_degradation_curve():
    cfg = BatteryConfig(type='LFP', capacity_kwh=50.0, max_charge_rate_kw=10, max_discharge_rate_kw=10)
    model = LFPModel(cfg)
    res = model.simulate_cycles(cycles=1000, dod=0.8, c_rate=0.5)
    assert res.soh < 1.0
    assert len(res.curve) == 1000


def test_lead_acid_sensitive_to_dod():
    cfg = BatteryConfig(type='Lead-Acid', capacity_kwh=20.0, max_charge_rate_kw=5, max_discharge_rate_kw=5)
    model = LeadAcidModel(cfg)
    r1 = model.simulate_cycles(cycles=500, dod=0.9, c_rate=0.8)
    r2 = model.simulate_cycles(cycles=500, dod=0.5, c_rate=0.8)
    assert r1.soh < r2.soh


def test_vrfb_minimal_degradation():
    cfg = BatteryConfig(type='VRFB', capacity_kwh=200.0, max_charge_rate_kw=50, max_discharge_rate_kw=50)
    model = VRFBModel(cfg)
    r = model.simulate_cycles(cycles=10000, dod=0.8, c_rate=1.0)
    # VRFB should retain high soh after 10k cycles (out of 20k EOL)
    assert r.soh > 0.5, f"VRFB SOH degradation too aggressive: {r.soh} (expected >0.5)"


def test_asset_integration(tmp_path):
    # quick run of asset function
    from energy_ml.assets.battery_models import battery_degradation_costs
    cfg = BatteryConfig(type='LFP', capacity_kwh=10.0, max_charge_rate_kw=3, max_discharge_rate_kw=3)
    user = make_user(cfg)
    out = battery_degradation_costs(user)
    assert out['battery_type'] == 'LFP'
    assert 'one_year' in out


if __name__ == '__main__':
    pytest.main([__file__])
