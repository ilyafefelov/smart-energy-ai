"""
Renewable Energy Forecasting Engine

Provides solar and wind generation forecasting based on:
- Weather data integration
- Geographic location
- Installed capacity
- Seasonal patterns
- Real-time generation modeling
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import math
import random

from energy_ml.user_config import UserConfigModel

logger = logging.getLogger(__name__)


class RenewableForecaster:
    """Engine for forecasting solar and wind generation."""
    
    def __init__(self):
        """Initialize renewable forecaster."""
        self.weather_cache = {}
        self.generation_models = {
            'solar': SolarGenerationModel(),
            'wind': WindGenerationModel()
        }
    
    def generate_forecasts(self, user_config: UserConfigModel) -> Dict[str, Any]:
        """Generate renewable energy forecasts.
        
        Args:
            user_config: User configuration with location and capacity data
            
        Returns:
            dict with solar, wind, and combined forecasts
        """
        try:
            # Get location (extend UserConfigModel to include this)
            latitude = getattr(user_config, 'latitude', 50.45)  # Default: Kyiv
            longitude = getattr(user_config, 'longitude', 30.52)
            
            # Get installed capacity (extend UserConfigModel)
            solar_capacity_kw = getattr(user_config, 'solar_capacity_kw', 0.0)
            wind_capacity_kw = getattr(user_config, 'wind_capacity_kw', 0.0)
            
            # Get weather data
            weather_data = self._get_weather_data(latitude, longitude)
            
            # Generate solar forecast
            solar_forecast = {}
            if solar_capacity_kw > 0:
                solar_forecast = self.generation_models['solar'].generate_forecast(
                    capacity_kw=solar_capacity_kw,
                    latitude=latitude,
                    longitude=longitude,
                    weather_data=weather_data
                )
            
            # Generate wind forecast
            wind_forecast = {}
            if wind_capacity_kw > 0:
                wind_forecast = self.generation_models['wind'].generate_forecast(
                    capacity_kw=wind_capacity_kw,
                    latitude=latitude,
                    longitude=longitude,
                    weather_data=weather_data
                )
            
            # Combine forecasts
            total_renewable = self._combine_forecasts(solar_forecast, wind_forecast)
            
            # Calculate capacity factors
            capacity_factors = self._calculate_capacity_factors(
                solar_forecast, wind_forecast, solar_capacity_kw, wind_capacity_kw
            )
            
            forecasts = {
                'solar_forecast': solar_forecast,
                'wind_forecast': wind_forecast,
                'total_renewable': total_renewable,
                'weather_data': weather_data,
                'capacity_factors': capacity_factors,
                'location': {'latitude': latitude, 'longitude': longitude},
                'installed_capacity': {
                    'solar_kw': solar_capacity_kw,
                    'wind_kw': wind_capacity_kw,
                    'total_kw': solar_capacity_kw + wind_capacity_kw
                },
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"Generated renewable forecasts for {solar_capacity_kw}kW solar + {wind_capacity_kw}kW wind")
            
            return forecasts
            
        except Exception as e:
            logger.error(f"Renewable forecasting failed: {e}")
            return {
                'solar_forecast': {},
                'wind_forecast': {},
                'total_renewable': {},
                'weather_data': {},
                'capacity_factors': {},
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _get_weather_data(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Get weather data for the location.
        
        In real implementation, this would call a weather API.
        For now, we'll use realistic mock data for Ukraine.
        """
        current_hour = datetime.now().hour
        current_date = datetime.now()
        
        # Mock weather data with seasonal and daily patterns
        season_factor = math.sin(2 * math.pi * current_date.timetuple().tm_yday / 365.25)
        
        # Solar irradiance (W/m²) - realistic for Ukraine
        base_irradiance = 600 + 300 * season_factor  # Higher in summer
        
        # Daily pattern for solar (sunrise to sunset)
        if 6 <= current_hour <= 18:
            # Solar day pattern (bell curve)
            hour_angle = (current_hour - 12) * math.pi / 6  # -π to π
            daily_factor = max(0, math.cos(hour_angle))
        else:
            daily_factor = 0
        
        solar_irradiance = base_irradiance * daily_factor
        
        # Add realistic variations
        cloud_cover = random.uniform(0.2, 0.8)  # 20-80% cloud cover
        solar_irradiance *= (1 - cloud_cover * 0.7)  # Clouds reduce irradiance
        
        # Wind data
        base_wind_speed = 5 + 3 * random.uniform(-1, 1)  # 2-8 m/s typical
        wind_gust_factor = 1 + random.uniform(-0.3, 0.5)  # Gusts
        wind_speed = max(0, base_wind_speed * wind_gust_factor)
        
        # Temperature
        base_temp = 15 + 15 * season_factor  # 0°C winter, 30°C summer
        daily_temp_variation = 10 * math.sin((current_hour - 6) * math.pi / 12)
        temperature = base_temp + daily_temp_variation + random.uniform(-3, 3)
        
        weather_data = {
            'solar_irradiance_w_m2': max(0, solar_irradiance),
            'wind_speed_m_s': wind_speed,
            'temperature_c': temperature,
            'cloud_cover_fraction': cloud_cover,
            'humidity_percent': random.uniform(40, 90),
            'pressure_hpa': 1013 + random.uniform(-20, 20),
            'visibility_km': random.uniform(5, 20),
            'current_hour': current_hour,
            'season_factor': season_factor,
            'location': f"{latitude:.2f}°N, {longitude:.2f}°E"
        }
        
        # Generate 24-hour forecast
        hourly_forecast = {}
        for h in range(24):
            forecast_hour = (current_hour + h) % 24
            
            # Solar forecast
            if 6 <= forecast_hour <= 18:
                hour_angle = (forecast_hour - 12) * math.pi / 6
                solar_daily_factor = max(0, math.cos(hour_angle))
            else:
                solar_daily_factor = 0
            
            forecast_solar = base_irradiance * solar_daily_factor * (1 - cloud_cover * 0.6)
            
            # Wind forecast (varies less predictably)
            wind_variation = random.uniform(0.7, 1.3)
            forecast_wind = base_wind_speed * wind_variation
            
            hourly_forecast[f'hour_{forecast_hour}'] = {
                'solar_irradiance_w_m2': max(0, forecast_solar),
                'wind_speed_m_s': max(0, forecast_wind),
                'temperature_c': base_temp + 8 * math.sin((forecast_hour - 6) * math.pi / 12)
            }
        
        weather_data['hourly_forecast'] = hourly_forecast
        
        return weather_data
    
    def _combine_forecasts(self, solar_forecast: Dict, wind_forecast: Dict) -> Dict[str, Any]:
        """Combine solar and wind forecasts into total renewable generation."""
        combined = {}
        
        # Current generation
        current_solar = solar_forecast.get('current_generation_kw', 0)
        current_wind = wind_forecast.get('current_generation_kw', 0)
        combined['current_generation_kw'] = current_solar + current_wind
        
        # Hourly forecast
        solar_hourly = solar_forecast.get('hourly_generation', {})
        wind_hourly = wind_forecast.get('hourly_generation', {})
        
        combined_hourly = {}
        for hour in range(24):
            hour_key = f'hour_{hour}'
            solar_gen = solar_hourly.get(hour_key, 0)
            wind_gen = wind_hourly.get(hour_key, 0)
            combined_hourly[hour_key] = solar_gen + wind_gen
        
        combined['hourly_generation'] = combined_hourly
        
        # Daily totals
        daily_solar = sum(solar_hourly.values()) if solar_hourly else 0
        daily_wind = sum(wind_hourly.values()) if wind_hourly else 0
        combined['daily_total_kwh'] = daily_solar + daily_wind
        
        # Peak generation
        peak_solar = max(solar_hourly.values()) if solar_hourly else 0
        peak_wind = max(wind_hourly.values()) if wind_hourly else 0
        combined['peak_generation_kw'] = peak_solar + peak_wind
        
        return combined
    
    def _calculate_capacity_factors(self, 
                                  solar_forecast: Dict, 
                                  wind_forecast: Dict,
                                  solar_capacity: float,
                                  wind_capacity: float) -> Dict[str, Any]:
        """Calculate capacity factors for renewable generation."""
        capacity_factors = {}
        
        # Solar capacity factor
        if solar_capacity > 0 and solar_forecast:
            solar_generation = solar_forecast.get('daily_total_kwh', 0)
            solar_theoretical_max = solar_capacity * 24  # kWh if running at 100% for 24h
            capacity_factors['solar'] = solar_generation / solar_theoretical_max if solar_theoretical_max > 0 else 0
        else:
            capacity_factors['solar'] = 0
        
        # Wind capacity factor
        if wind_capacity > 0 and wind_forecast:
            wind_generation = wind_forecast.get('daily_total_kwh', 0)
            wind_theoretical_max = wind_capacity * 24  # kWh if running at 100% for 24h
            capacity_factors['wind'] = wind_generation / wind_theoretical_max if wind_theoretical_max > 0 else 0
        else:
            capacity_factors['wind'] = 0
        
        # Combined capacity factor
        total_capacity = solar_capacity + wind_capacity
        if total_capacity > 0:
            total_generation = (solar_forecast.get('daily_total_kwh', 0) + 
                              wind_forecast.get('daily_total_kwh', 0))
            total_theoretical_max = total_capacity * 24
            capacity_factors['combined'] = total_generation / total_theoretical_max if total_theoretical_max > 0 else 0
        else:
            capacity_factors['combined'] = 0
        
        return capacity_factors
    
    def integrate_with_prediction(self, 
                                prediction: Dict[str, Any],
                                renewable_data: Dict[str, Any]) -> Dict[str, Any]:
        """Integrate renewable generation with energy trading prediction."""
        if not renewable_data or renewable_data.get('timestamp') is None:
            return prediction
        
        current_generation = renewable_data.get('total_renewable', {}).get('current_generation_kw', 0)
        hourly_generation = renewable_data.get('total_renewable', {}).get('hourly_generation', {})
        
        action = prediction.get('action', 'HOLD')
        confidence = prediction.get('confidence', 0.5)
        reasoning = prediction.get('reasoning', '')
        
        # Modify decision based on renewable generation
        renewable_enhanced = prediction.copy()
        
        if current_generation > 5:  # Significant renewable generation
            if action == 'BUY':
                # If renewable generation is high, reduce need to buy from grid
                renewable_enhanced['action'] = 'HOLD'
                renewable_enhanced['confidence'] = min(0.9, confidence + 0.1)
                renewable_enhanced['reasoning'] = f"{reasoning} Renewable generation ({current_generation:.1f} kW) reduces grid dependency."
            
            elif action == 'SELL':
                # Renewable generation supports selling decision
                renewable_enhanced['confidence'] = min(1.0, confidence + 0.15)
                renewable_enhanced['reasoning'] = f"{reasoning} High renewable generation ({current_generation:.1f} kW) supports export."
        
        # Add renewable integration details
        renewable_enhanced.update({
            'renewable_generation_kw': current_generation,
            'renewable_forecast_available': len(hourly_generation) > 0,
            'next_hour_renewable_kw': hourly_generation.get(f'hour_{(datetime.now().hour + 1) % 24}', 0),
            'renewable_capacity_factor': renewable_data.get('capacity_factors', {}).get('combined', 0),
            'renewable_integration_applied': True
        })
        
        return renewable_enhanced


class SolarGenerationModel:
    """Model for solar PV generation forecasting."""
    
    def generate_forecast(self, 
                         capacity_kw: float,
                         latitude: float,
                         longitude: float,
                         weather_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate solar generation forecast."""
        try:
            current_irradiance = weather_data.get('solar_irradiance_w_m2', 0)
            temperature = weather_data.get('temperature_c', 25)
            
            # Solar panel efficiency model
            panel_efficiency = self._calculate_panel_efficiency(temperature)
            
            # Current generation
            # Standard Test Conditions: 1000 W/m², 25°C
            stc_irradiance = 1000  # W/m²
            current_generation_kw = (capacity_kw * (current_irradiance / stc_irradiance) * 
                                   panel_efficiency)
            
            # Hourly generation forecast
            hourly_generation = {}
            hourly_forecast = weather_data.get('hourly_forecast', {})
            
            daily_total = 0
            for hour_key, hour_weather in hourly_forecast.items():
                hour_irradiance = hour_weather.get('solar_irradiance_w_m2', 0)
                hour_temp = hour_weather.get('temperature_c', 25)
                hour_efficiency = self._calculate_panel_efficiency(hour_temp)
                
                hour_generation = (capacity_kw * (hour_irradiance / stc_irradiance) * 
                                 hour_efficiency)
                hourly_generation[hour_key] = max(0, hour_generation)
                daily_total += max(0, hour_generation)
            
            solar_forecast = {
                'current_generation_kw': max(0, current_generation_kw),
                'hourly_generation': hourly_generation,
                'daily_total_kwh': daily_total,
                'peak_generation_kw': max(hourly_generation.values()) if hourly_generation else 0,
                'panel_efficiency': panel_efficiency,
                'current_irradiance_w_m2': current_irradiance,
                'capacity_kw': capacity_kw,
                'performance_ratio': current_generation_kw / capacity_kw if capacity_kw > 0 else 0
            }
            
            return solar_forecast
            
        except Exception as e:
            logger.error(f"Solar forecast generation failed: {e}")
            return {'error': str(e)}
    
    def _calculate_panel_efficiency(self, temperature: float) -> float:
        """Calculate solar panel efficiency based on temperature."""
        # Standard efficiency at 25°C
        standard_efficiency = 0.20  # 20% efficiency
        
        # Temperature coefficient (typically -0.4%/°C for silicon)
        temp_coefficient = -0.004  # per °C
        
        # Efficiency at actual temperature
        efficiency = standard_efficiency * (1 + temp_coefficient * (temperature - 25))
        
        # Clamp to reasonable bounds
        return max(0.10, min(0.25, efficiency))


class WindGenerationModel:
    """Model for wind turbine generation forecasting."""
    
    def generate_forecast(self,
                         capacity_kw: float,
                         latitude: float,
                         longitude: float,
                         weather_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate wind generation forecast."""
        try:
            current_wind_speed = weather_data.get('wind_speed_m_s', 0)
            
            # Current generation using power curve
            current_generation_kw = self._wind_power_curve(current_wind_speed, capacity_kw)
            
            # Hourly generation forecast
            hourly_generation = {}
            hourly_forecast = weather_data.get('hourly_forecast', {})
            
            daily_total = 0
            for hour_key, hour_weather in hourly_forecast.items():
                hour_wind_speed = hour_weather.get('wind_speed_m_s', 0)
                hour_generation = self._wind_power_curve(hour_wind_speed, capacity_kw)
                
                hourly_generation[hour_key] = hour_generation
                daily_total += hour_generation
            
            wind_forecast = {
                'current_generation_kw': current_generation_kw,
                'hourly_generation': hourly_generation,
                'daily_total_kwh': daily_total,
                'peak_generation_kw': max(hourly_generation.values()) if hourly_generation else 0,
                'current_wind_speed_m_s': current_wind_speed,
                'capacity_kw': capacity_kw,
                'capacity_factor': current_generation_kw / capacity_kw if capacity_kw > 0 else 0
            }
            
            return wind_forecast
            
        except Exception as e:
            logger.error(f"Wind forecast generation failed: {e}")
            return {'error': str(e)}
    
    def _wind_power_curve(self, wind_speed_m_s: float, rated_power_kw: float) -> float:
        """Calculate wind turbine power output using typical power curve."""
        # Typical wind turbine parameters
        cut_in_speed = 3.0   # m/s - minimum wind speed
        rated_speed = 12.0   # m/s - rated wind speed (full power)
        cut_out_speed = 25.0 # m/s - maximum wind speed (shutdown)
        
        if wind_speed_m_s < cut_in_speed:
            return 0.0
        elif wind_speed_m_s > cut_out_speed:
            return 0.0  # Safety shutdown
        elif wind_speed_m_s >= rated_speed:
            return rated_power_kw  # Full power
        else:
            # Cubic power curve between cut-in and rated speed
            # P = 0.5 * ρ * A * v³ * Cp (simplified to cubic relationship)
            power_ratio = ((wind_speed_m_s - cut_in_speed) / (rated_speed - cut_in_speed)) ** 3
            return rated_power_kw * power_ratio