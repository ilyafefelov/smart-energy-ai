"""
Economic Modeling for Energy Storage Systems

LCOS (Levelized Cost of Storage) and related economic calculations
for battery energy storage systems.

Thesis Relevance: Provides comprehensive economic framework for comparing
different storage technologies and operating strategies.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class BatteryTechnology(Enum):
    """Battery technology types with different characteristics"""
    LFP = "Lithium Iron Phosphate"
    NMC = "Nickel Manganese Cobalt"  
    LEAD_ACID = "Lead Acid"
    SODIUM_ION = "Sodium Ion"


@dataclass
class EconomicParameters:
    """Economic parameters for LCOS calculation"""
    capex_per_kwh: float  # Capital expenditure ($/kWh)
    opex_per_kwh_year: float  # Operating expenditure ($/kWh/year)
    replacement_cost_ratio: float  # Replacement cost as ratio of capex
    discount_rate: float  # Annual discount rate
    system_lifetime_years: int  # System lifetime
    cycle_life: int  # Expected cycle life
    calendar_life_years: int  # Calendar aging limit
    roundtrip_efficiency: float  # Round-trip efficiency
    dod_limit: float  # Maximum depth of discharge


@dataclass
class OperationProfile:
    """Battery operation profile for economic analysis"""
    daily_cycles: float  # Average cycles per day
    seasonal_variation: float  # Seasonal capacity factor variation
    capacity_factor: float  # Overall capacity utilization
    grid_services_revenue: float  # $/kWh from grid services
    energy_arbitrage_spread: float  # Average price spread ($/MWh)


class EconomicModel:
    """
    Comprehensive economic model for energy storage systems.
    
    Calculates LCOS, NPV, IRR, and other economic metrics.
    """
    
    # Technology-specific parameters
    TECHNOLOGY_PARAMS = {
        BatteryTechnology.LFP: EconomicParameters(
            capex_per_kwh=150.0,
            opex_per_kwh_year=2.0,
            replacement_cost_ratio=0.7,
            discount_rate=0.08,
            system_lifetime_years=20,
            cycle_life=6000,
            calendar_life_years=15,
            roundtrip_efficiency=0.95,
            dod_limit=0.9
        ),
        BatteryTechnology.NMC: EconomicParameters(
            capex_per_kwh=120.0,
            opex_per_kwh_year=2.5,
            replacement_cost_ratio=0.75,
            discount_rate=0.08,
            system_lifetime_years=20,
            cycle_life=4000,
            calendar_life_years=12,
            roundtrip_efficiency=0.92,
            dod_limit=0.85
        ),
        BatteryTechnology.LEAD_ACID: EconomicParameters(
            capex_per_kwh=80.0,
            opex_per_kwh_year=8.0,
            replacement_cost_ratio=0.9,
            discount_rate=0.08,
            system_lifetime_years=20,
            cycle_life=1500,
            calendar_life_years=8,
            roundtrip_efficiency=0.85,
            dod_limit=0.5
        ),
        BatteryTechnology.SODIUM_ION: EconomicParameters(
            capex_per_kwh=110.0,
            opex_per_kwh_year=1.8,
            replacement_cost_ratio=0.7,
            discount_rate=0.08,
            system_lifetime_years=20,
            cycle_life=5000,
            calendar_life_years=18,
            roundtrip_efficiency=0.90,
            dod_limit=0.95
        )
    }
    
    def __init__(self, technology: BatteryTechnology, 
                 capacity_kwh: float = 280.0):
        self.technology = technology
        self.capacity_kwh = capacity_kwh
        self.params = self.TECHNOLOGY_PARAMS[technology]
        
    def calculate_lcos(self, operation_profile: OperationProfile) -> Dict[str, float]:
        """
        Calculate Levelized Cost of Storage (LCOS).
        
        LCOS = (Capex + PV(Opex) + PV(Replacement)) / PV(Energy Throughput)
        
        Args:
            operation_profile: Battery operation characteristics
            
        Returns:
            Dictionary with LCOS breakdown
        """
        # Calculate energy throughput per year
        usable_capacity = self.capacity_kwh * self.params.dod_limit
        annual_throughput = (
            usable_capacity * operation_profile.daily_cycles * 365 * 
            operation_profile.capacity_factor
        )
        
        # Determine limiting factor (cycle life vs calendar life)
        cycle_lifetime = self.params.cycle_life / (
            operation_profile.daily_cycles * 365
        )
        limiting_lifetime = min(
            cycle_lifetime, 
            self.params.calendar_life_years,
            self.params.system_lifetime_years
        )
        
        # Capital costs
        initial_capex = self.capacity_kwh * self.params.capex_per_kwh
        
        # Operating costs (present value)
        pv_opex = 0
        for year in range(1, int(limiting_lifetime) + 1):
            annual_opex = self.capacity_kwh * self.params.opex_per_kwh_year
            discount_factor = (1 + self.params.discount_rate) ** year
            pv_opex += annual_opex / discount_factor
            
        # Replacement costs (if needed)
        pv_replacement = 0
        if limiting_lifetime < self.params.system_lifetime_years:
            replacement_years = np.arange(
                limiting_lifetime, 
                self.params.system_lifetime_years, 
                limiting_lifetime
            )
            for year in replacement_years:
                replacement_cost = (
                    initial_capex * self.params.replacement_cost_ratio
                )
                discount_factor = (1 + self.params.discount_rate) ** year
                pv_replacement += replacement_cost / discount_factor
                
        # Total present value of costs
        total_pv_costs = initial_capex + pv_opex + pv_replacement
        
        # Present value of energy throughput
        pv_throughput = 0
        for year in range(1, self.params.system_lifetime_years + 1):
            yearly_throughput = annual_throughput
            # Account for degradation (linear assumption)
            degradation_factor = 1 - (year - 1) * 0.02  # 2% per year
            yearly_throughput *= max(0.8, degradation_factor)
            
            discount_factor = (1 + self.params.discount_rate) ** year
            pv_throughput += yearly_throughput / discount_factor
            
        # LCOS calculation
        lcos_per_kwh = total_pv_costs / pv_throughput if pv_throughput > 0 else float('inf')
        lcos_per_mwh = lcos_per_kwh * 1000  # Convert to $/MWh
        
        return {
            "lcos_usd_per_kwh": lcos_per_kwh,
            "lcos_usd_per_mwh": lcos_per_mwh,
            "total_costs": total_pv_costs,
            "capex_component": initial_capex,
            "opex_component": pv_opex,
            "replacement_component": pv_replacement,
            "total_throughput_mwh": pv_throughput / 1000,
            "effective_lifetime_years": limiting_lifetime
        }
        
    def calculate_arbitrage_value(self, 
                                 price_spreads: List[float],
                                 operation_profile: OperationProfile) -> Dict[str, float]:
        """
        Calculate value from energy arbitrage operations.
        
        Args:
            price_spreads: Historical price spreads ($/MWh)
            operation_profile: Operation characteristics
            
        Returns:
            Arbitrage value analysis
        """
        # Average arbitrage opportunity
        avg_spread = np.mean(price_spreads)
        spread_std = np.std(price_spreads)
        
        # Usable capacity for arbitrage
        usable_capacity = self.capacity_kwh * self.params.dod_limit
        
        # Annual arbitrage cycles
        annual_cycles = operation_profile.daily_cycles * 365
        
        # Efficiency losses
        efficiency_factor = self.params.roundtrip_efficiency
        
        # Annual arbitrage value
        annual_arbitrage_mwh = (usable_capacity / 1000) * annual_cycles
        annual_gross_value = annual_arbitrage_mwh * avg_spread
        annual_net_value = annual_gross_value * efficiency_factor
        
        # Present value over system lifetime
        pv_arbitrage_value = 0
        for year in range(1, self.params.system_lifetime_years + 1):
            # Degradation factor
            degradation_factor = 1 - (year - 1) * 0.02
            yearly_value = annual_net_value * max(0.8, degradation_factor)
            
            discount_factor = (1 + self.params.discount_rate) ** year
            pv_arbitrage_value += yearly_value / discount_factor
            
        return {
            "annual_arbitrage_mwh": annual_arbitrage_mwh,
            "avg_price_spread": avg_spread,
            "annual_gross_value": annual_gross_value,
            "annual_net_value": annual_net_value,
            "pv_arbitrage_value": pv_arbitrage_value,
            "arbitrage_volatility": spread_std
        }
        
    def calculate_npv_irr(self, 
                         cash_flows: List[float]) -> Tuple[float, Optional[float]]:
        """
        Calculate Net Present Value and Internal Rate of Return.
        
        Args:
            cash_flows: Annual cash flows (negative for costs, positive for revenues)
            
        Returns:
            Tuple of (NPV, IRR)
        """
        # NPV calculation
        npv = 0
        for year, cash_flow in enumerate(cash_flows):
            discount_factor = (1 + self.params.discount_rate) ** year
            npv += cash_flow / discount_factor
            
        # IRR calculation using Newton-Raphson method
        irr = None
        try:
            # Initial guess
            rate = 0.1
            for _ in range(100):  # Maximum iterations
                npv_at_rate = sum(
                    cf / ((1 + rate) ** year) 
                    for year, cf in enumerate(cash_flows)
                )
                
                # Derivative (for Newton-Raphson)
                dnpv_dr = sum(
                    -year * cf / ((1 + rate) ** (year + 1))
                    for year, cf in enumerate(cash_flows)
                    if year > 0
                )
                
                if abs(dnpv_dr) < 1e-10:
                    break
                    
                rate_new = rate - npv_at_rate / dnpv_dr
                
                if abs(rate_new - rate) < 1e-6:
                    irr = rate_new
                    break
                    
                rate = rate_new
                
        except:
            irr = None  # IRR calculation failed
            
        return npv, irr
        
    def compare_technologies(self, 
                           operation_profile: OperationProfile,
                           price_spreads: List[float]) -> Dict[str, Dict]:
        """
        Compare different battery technologies for the same application.
        
        Args:
            operation_profile: Operation characteristics
            price_spreads: Historical price spreads
            
        Returns:
            Comparison results for all technologies
        """
        comparison_results = {}
        
        for tech in BatteryTechnology:
            # Create model for this technology
            tech_model = EconomicModel(tech, self.capacity_kwh)
            
            # Calculate LCOS
            lcos_results = tech_model.calculate_lcos(operation_profile)
            
            # Calculate arbitrage value
            arbitrage_results = tech_model.calculate_arbitrage_value(
                price_spreads, operation_profile
            )
            
            # Calculate net economics
            net_annual_value = (
                arbitrage_results["annual_net_value"] -
                tech_model.capacity_kwh * tech_model.params.opex_per_kwh_year
            )
            
            # Simple payback period
            payback_years = (
                tech_model.params.capex_per_kwh * tech_model.capacity_kwh /
                max(1, net_annual_value)
            )
            
            comparison_results[tech.value] = {
                "lcos": lcos_results,
                "arbitrage": arbitrage_results,
                "net_annual_value": net_annual_value,
                "payback_years": payback_years,
                "technology": tech
            }
            
        return comparison_results
        
    def sensitivity_analysis(self, 
                           base_operation_profile: OperationProfile,
                           parameter_ranges: Dict[str, Tuple[float, float]],
                           num_points: int = 5) -> Dict[str, List[float]]:
        """
        Perform sensitivity analysis on key parameters.
        
        Args:
            base_operation_profile: Base case operation profile
            parameter_ranges: Dictionary of parameter ranges to test
            num_points: Number of points to test in each range
            
        Returns:
            Sensitivity analysis results
        """
        results = {}
        
        for param_name, (min_val, max_val) in parameter_ranges.items():
            param_values = np.linspace(min_val, max_val, num_points)
            lcos_values = []
            
            for param_val in param_values:
                # Create modified operation profile
                profile = OperationProfile(
                    daily_cycles=base_operation_profile.daily_cycles,
                    seasonal_variation=base_operation_profile.seasonal_variation,
                    capacity_factor=base_operation_profile.capacity_factor,
                    grid_services_revenue=base_operation_profile.grid_services_revenue,
                    energy_arbitrage_spread=base_operation_profile.energy_arbitrage_spread
                )
                
                # Modify the specific parameter
                if param_name == "daily_cycles":
                    profile.daily_cycles = param_val
                elif param_name == "capacity_factor":
                    profile.capacity_factor = param_val
                elif param_name == "arbitrage_spread":
                    profile.energy_arbitrage_spread = param_val
                elif param_name == "capex_per_kwh":
                    # Temporarily modify capex
                    original_capex = self.params.capex_per_kwh
                    self.params.capex_per_kwh = param_val
                    
                lcos_result = self.calculate_lcos(profile)
                lcos_values.append(lcos_result["lcos_usd_per_mwh"])
                
                # Restore original capex if modified
                if param_name == "capex_per_kwh":
                    self.params.capex_per_kwh = original_capex
                    
            results[param_name] = {
                "parameter_values": param_values.tolist(),
                "lcos_values": lcos_values
            }
            
        return results


# Example usage and validation
if __name__ == "__main__":
    # Example operation profile for Ukrainian market
    ukraine_operation = OperationProfile(
        daily_cycles=1.2,  # 1.2 cycles per day average
        seasonal_variation=0.3,  # 30% seasonal variation
        capacity_factor=0.8,  # 80% capacity utilization
        grid_services_revenue=0.0,  # No grid services initially
        energy_arbitrage_spread=45.0  # $45/MWh average spread
    )
    
    # Historical price spreads (example)
    price_spreads = [30, 45, 60, 25, 55, 40, 35, 50, 65, 30]  # $/MWh
    
    print("Energy Storage Economic Analysis")
    print("=" * 50)
    
    # Compare all technologies
    lfp_model = EconomicModel(BatteryTechnology.LFP, 280.0)
    comparison = lfp_model.compare_technologies(ukraine_operation, price_spreads)
    
    print("\nTechnology Comparison:")
    print("-" * 30)
    
    for tech_name, results in comparison.items():
        lcos = results["lcos"]["lcos_usd_per_mwh"]
        payback = results["payback_years"]
        annual_value = results["net_annual_value"]
        
        print(f"\n{tech_name}:")
        print(f"  LCOS: ${lcos:.2f}/MWh")
        print(f"  Payback: {payback:.1f} years")
        print(f"  Annual Net Value: ${annual_value:,.0f}")
        
    # Detailed LFP analysis
    print(f"\n\nDetailed LFP Analysis:")
    print("-" * 30)
    
    lcos_details = lfp_model.calculate_lcos(ukraine_operation)
    arbitrage_details = lfp_model.calculate_arbitrage_value(
        price_spreads, ukraine_operation
    )
    
    print(f"LCOS Breakdown:")
    print(f"  Total LCOS: ${lcos_details['lcos_usd_per_mwh']:.2f}/MWh")
    print(f"  Capex Component: ${lcos_details['capex_component']:,.0f}")
    print(f"  Opex Component: ${lcos_details['opex_component']:,.0f}")
    print(f"  Replacement Component: ${lcos_details['replacement_component']:,.0f}")
    print(f"  Effective Lifetime: {lcos_details['effective_lifetime_years']:.1f} years")
    
    print(f"\nArbitrage Value:")
    print(f"  Annual Throughput: {arbitrage_details['annual_arbitrage_mwh']:.1f} MWh")
    print(f"  Annual Gross Value: ${arbitrage_details['annual_gross_value']:,.0f}")
    print(f"  Annual Net Value: ${arbitrage_details['annual_net_value']:,.0f}")
    print(f"  PV Arbitrage Value: ${arbitrage_details['pv_arbitrage_value']:,.0f}")
    
    # Sensitivity analysis
    sensitivity_params = {
        "daily_cycles": (0.5, 2.0),
        "capacity_factor": (0.5, 1.0),
        "arbitrage_spread": (20, 80),
        "capex_per_kwh": (100, 200)
    }
    
    sensitivity_results = lfp_model.sensitivity_analysis(
        ukraine_operation, sensitivity_params
    )
    
    print(f"\nSensitivity Analysis (LCOS Range):")
    print("-" * 40)
    for param, data in sensitivity_results.items():
        min_lcos = min(data["lcos_values"])
        max_lcos = max(data["lcos_values"])
        print(f"{param}: ${min_lcos:.2f} - ${max_lcos:.2f}/MWh")