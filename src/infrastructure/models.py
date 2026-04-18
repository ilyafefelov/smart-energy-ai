"""
SQLAlchemy ORM models for Smart Energy AI database
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Index, Boolean, JSON
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.sql import func
from datetime import datetime
from .db import Base


class WeatherForecast(Base):
    """Weather forecast data from Open-Meteo API"""
    __tablename__ = "weather_forecasts"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, unique=True, index=True)
    temperature = Column(Float, nullable=True)
    solar_radiation = Column(Float, nullable=True)  # W/m²
    cloudcover = Column(Float, nullable=True)  # %
    wind_speed = Column(Float, nullable=True)  # m/s
    humidity = Column(Float, nullable=True)  # %
    created_at = Column(DateTime, default=func.now())


class MarketPrice(Base):
    """Electricity market prices from OREE Ukraine"""
    __tablename__ = "market_prices"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, unique=True, index=True)
    price_eur_mwh = Column(Float, nullable=False)
    price_uah_mwh = Column(Float, nullable=True)
    min_price = Column(Float, nullable=True)
    max_price = Column(Float, nullable=True)
    source = Column(String, default="oree_api")
    created_at = Column(DateTime, default=func.now())


class OptimizationHistory(Base):
    """Historical optimization decisions & feedback loop"""
    __tablename__ = "optimization_history"

    id = Column(Integer, primary_key=True, index=True)
    execution_key = Column(String(64), nullable=False, unique=True, index=True)
    command_id = Column(String(128), nullable=True, index=True)
    schedule_id = Column(String(128), nullable=True, index=True)
    tenant_id = Column(String(128), nullable=True, index=True)
    execution_source = Column(String(64), nullable=False, default="unknown")
    timestamp = Column(DateTime, nullable=False, index=True)
    predicted_action = Column(Integer, nullable=False)  # 0=charge, 1=discharge, 2=sell, 3=buy, 4=idle
    actual_action = Column(Integer, nullable=True)  # What SCADA actually executed
    cost_baseline = Column(Float, nullable=True)  # Cost if always buying
    cost_rl = Column(Float, nullable=True)  # Actual cost with RL recommendation
    price_uah_kwh = Column(Float, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    energy_kwh = Column(Float, nullable=True)
    economics_method = Column(String(64), nullable=True)
    economics_version = Column(String(64), nullable=True)
    fallback_reason = Column(String, nullable=True)
    price_source = Column(String(64), nullable=True)
    tariff_window = Column(String(32), nullable=True)
    interval_start = Column(DateTime, nullable=True)
    interval_end = Column(DateTime, nullable=True)
    battery_soc_start = Column(Float, nullable=True)  # Battery % at start
    battery_soc_end = Column(Float, nullable=True)  # Battery % at end
    solar_actual = Column(Float, nullable=True)  # Actual solar generation (kW)
    load_actual = Column(Float, nullable=True)  # Actual load (kW)
    decision_source = Column(String(32), nullable=True)
    execution_status = Column(String(32), nullable=True)
    event_type = Column(String(32), nullable=True)
    mode_from = Column(String(32), nullable=True)
    mode_to = Column(String(32), nullable=True)
    realized_revenue_uah = Column(Float, nullable=True)
    realized_cost_uah = Column(Float, nullable=True)
    realized_net_uah = Column(Float, nullable=True)
    decision_snapshot = Column(JSON, nullable=True)
    is_reconciled = Column(Boolean, nullable=False, default=False)
    reconciled_at = Column(DateTime, nullable=True)
    reconciliation_note = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class RLTrainingLog(Base):
    """RL agent training metrics"""
    __tablename__ = "rl_training_logs"

    id = Column(Integer, primary_key=True, index=True)
    training_date = Column(DateTime, nullable=False, index=True)
    episode_count = Column(Integer, nullable=False)
    avg_reward = Column(Float, nullable=True)
    total_cost_savings = Column(Float, nullable=True)  # $
    model_version = Column(String, nullable=True)  # e.g., "v1_ppo_2026_01_29"
    validation_loss = Column(Float, nullable=True)
    created_at = Column(DateTime, default=func.now())


class SiteConfig(Base):
    """Site/plant configuration"""
    __tablename__ = "config"

    id = Column(Integer, primary_key=True, index=True)
    site_name = Column(String, nullable=False)
    location_lat = Column(Float, nullable=True)
    location_lon = Column(Float, nullable=True)
    solar_capacity_kw = Column(Float, default=150.0)
    wind_capacity_kw = Column(Float, default=0.0)
    battery_capacity_kwh = Column(Float, default=300.0)
    battery_max_charge_rate_kw = Column(Float, default=100.0)
    diesel_gen_capacity_kw = Column(Float, default=50.0)
    diesel_fuel_cost_per_liter = Column(Float, default=52.0)  # UAH
    created_at = Column(DateTime, default=func.now())


# Index definitions
__table_args__ = (
    Index('idx_weather_timestamp', WeatherForecast.timestamp),
    Index('idx_prices_timestamp', MarketPrice.timestamp),
    Index('idx_history_timestamp', OptimizationHistory.timestamp),
    Index('idx_history_tenant_timestamp', OptimizationHistory.tenant_id, OptimizationHistory.timestamp),
    Index('idx_training_date', RLTrainingLog.training_date),
)
