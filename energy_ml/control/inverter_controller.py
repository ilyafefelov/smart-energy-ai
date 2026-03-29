"""
Inverter Controller - Real Battery Control System

This module implements the core control infrastructure for Smart Energy AI.
Phase 1: Virtual inverter for testing and development
Phase 2: Real hardware integration via MQTT/Modbus

Key Features:
- Real-time command execution with validation
- Command history and logging for Dagster Asset Metadata  
- SOC tracking and power management
- Support for manual, automatic, and scheduled control modes
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import asyncio
import logging
from datetime import datetime
import json
import os

from .inverter_controller_support import (
    append_command_result,
    build_command_log,
    build_persisted_status_data,
    build_schedule_entry,
    build_status_payload,
    calculate_charge_completion_time,
    calculate_discharge_completion_time,
    estimate_completion,
    retain_recent_scheduled_commands,
    trim_command_history,
    validate_command,
)

# Configure logging
logger = logging.getLogger(__name__)

class ControlCommand(str, Enum):
    """Battery control commands"""
    CHARGE = "charge"
    DISCHARGE = "discharge" 
    HOLD = "hold"
    AUTO = "auto"

class ControlMode(str, Enum):
    """System control modes"""
    MANUAL = "manual"
    AUTOMATIC = "automatic"
    SCHEDULED = "scheduled"

@dataclass
class ControlAction:
    """Battery control action with metadata"""
    command: ControlCommand
    power_kw: float
    duration_minutes: Optional[int] = None
    priority: int = 1  # 1=low, 5=high
    reason: str = ""
    user_id: str = "system"
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/API"""
        return {
            'command': self.command.value,
            'power_kw': self.power_kw,
            'duration_minutes': self.duration_minutes,
            'priority': self.priority,
            'reason': self.reason,
            'user_id': self.user_id,
            'timestamp': self.timestamp.isoformat()
        }

class VirtualInverterController:
    """
    Virtual inverter for Phase 1. Will be replaced with MQTT/Modbus in Phase 2.
    
    Provides real battery control simulation with:
    - SOC tracking and validation
    - Power limit enforcement  
    - Command history for ML pipeline integration
    - Status reporting for dashboard
    """
    
    def __init__(self, 
                 battery_capacity_kwh: float = 10.0, 
                 max_power_kw: float = 5.0,
                 initial_soc: float = 0.5):
        self.battery_capacity_kwh = battery_capacity_kwh
        self.max_power_kw = max_power_kw
        self.current_soc = initial_soc  # Start at specified SOC
        self.current_power_kw = 0.0
        self.mode = ControlMode.AUTOMATIC
        self.active_command = None
        self.command_history: List[Dict[str, Any]] = []
        self.scheduled_commands: List[Dict[str, Any]] = []
        
        # Command execution tracking
        self.last_command_time = None
        self.estimated_completion_time = None
        
        # Create outputs directory for status persistence
        self.status_file = "energy_ml/outputs/control_status.json"
        os.makedirs(os.path.dirname(self.status_file), exist_ok=True)
        
    async def execute_command(self, action: ControlAction) -> Dict[str, Any]:
        """
        Execute control command with validation and logging.
        
        Args:
            action: ControlAction to execute
            
        Returns:
            Dict with execution results and new system status
            
        Raises:
            ValueError: If command validation fails
        """
        logger.info(f"Executing command: {action.command} {action.power_kw}kW - {action.reason}")
        
        # Validate command
        validation_result = self._validate_command(action)
        if not validation_result['valid']:
            raise ValueError(f"Invalid command: {validation_result['reason']}")
            
        # Log command for Dagster Asset Metadata
        command_log = build_command_log(action, self.current_soc, self.current_power_kw)
        
        # Execute command
        if action.command == ControlCommand.CHARGE:
            await self._start_charging(action.power_kw)
        elif action.command == ControlCommand.DISCHARGE:
            await self._start_discharging(action.power_kw)
        elif action.command == ControlCommand.HOLD:
            await self._hold_position()
        elif action.command == ControlCommand.AUTO:
            await self._enable_auto_mode()
            
        # Update command log with results
        estimated_completion = self._estimate_completion(action)
        append_command_result(
            command_log,
            self.current_soc,
            self.current_power_kw,
            estimated_completion,
        )
        
        self.command_history.append(command_log)
        
        # Keep only last 100 commands in memory
        self.command_history = trim_command_history(self.command_history)
            
        # Update active command
        self.active_command = action
        self.last_command_time = datetime.now()
        
        # Save status to file
        await self._save_status()
        
        return {
            'success': True,
            'new_soc': self.current_soc,
            'power_kw': self.current_power_kw,
            'estimated_completion': estimated_completion,
            'command_id': len(self.command_history)
        }
    
    async def schedule_command(self, 
                             action: ControlAction, 
                             scheduled_time: datetime) -> Dict[str, Any]:
        """Schedule a command for future execution"""
        schedule_entry = build_schedule_entry(
            action,
            scheduled_time,
            len(self.scheduled_commands),
        )
        
        self.scheduled_commands.append(schedule_entry)
        logger.info(f"Scheduled command: {action.command} at {scheduled_time}")
        
        await self._save_status()
        
        return {
            'success': True,
            'schedule_id': schedule_entry['id'],
            'scheduled_time': scheduled_time.isoformat()
        }
        
    async def cancel_scheduled_command(self, schedule_id: str) -> bool:
        """Cancel a scheduled command"""
        for i, cmd in enumerate(self.scheduled_commands):
            if cmd['id'] == schedule_id:
                self.scheduled_commands.pop(i)
                await self._save_status()
                logger.info(f"Cancelled scheduled command: {schedule_id}")
                return True
        return False
        
    async def process_scheduled_commands(self):
        """Process any pending scheduled commands"""
        now = datetime.now()
        executed_commands = []
        
        for cmd in self.scheduled_commands:
            if cmd['status'] == 'pending':
                scheduled_time = datetime.fromisoformat(cmd['scheduled_time'])
                if now >= scheduled_time:
                    # Execute the command
                    action_data = cmd['action'] 
                    action = ControlAction(
                        command=ControlCommand(action_data['command']),
                        power_kw=action_data['power_kw'],
                        duration_minutes=action_data['duration_minutes'],
                        reason=f"Scheduled: {action_data['reason']}",
                        user_id=action_data['user_id']
                    )
                    
                    try:
                        result = await self.execute_command(action)
                        cmd['status'] = 'executed'
                        cmd['executed_at'] = now.isoformat()
                        cmd['result'] = result
                        executed_commands.append(cmd)
                        logger.info(f"Executed scheduled command: {cmd['id']}")
                    except Exception as e:
                        cmd['status'] = 'failed'
                        cmd['error'] = str(e)
                        logger.error(f"Failed to execute scheduled command {cmd['id']}: {e}")
                        
        # Clean up old executed commands (keep for 24 hours)
        self.scheduled_commands = retain_recent_scheduled_commands(
            self.scheduled_commands,
            now,
        )
        
        if executed_commands:
            await self._save_status()
            
        return executed_commands
    
    def get_status(self) -> Dict[str, Any]:
        """Get current system status"""
        return build_status_payload(
            current_soc=self.current_soc,
            current_power_kw=self.current_power_kw,
            mode_value=self.mode.value,
            active_command=self.active_command,
            battery_capacity_kwh=self.battery_capacity_kwh,
            max_power_kw=self.max_power_kw,
            estimated_completion_time=self.estimated_completion_time,
            scheduled_commands=self.scheduled_commands,
        )
        
    def get_command_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent command history"""
        return self.command_history[-limit:] if limit else self.command_history
        
    def get_scheduled_commands(self) -> List[Dict[str, Any]]:
        """Get all scheduled commands"""
        return [cmd for cmd in self.scheduled_commands if cmd['status'] == 'pending']
    
    def _validate_command(self, action: ControlAction) -> Dict[str, Any]:
        """Validate command before execution"""
        
        return validate_command(action, self.current_soc, self.max_power_kw)
    
    async def _start_charging(self, power_kw: float):
        """Start charging at specified power"""
        self.current_power_kw = abs(power_kw)  # Ensure positive for charging
        self.estimated_completion_time = self._calculate_charge_completion_time(power_kw)
        logger.info(f"Started charging at {power_kw}kW")
        
    async def _start_discharging(self, power_kw: float):
        """Start discharging at specified power"""
        self.current_power_kw = -abs(power_kw)  # Ensure negative for discharging  
        self.estimated_completion_time = self._calculate_discharge_completion_time(power_kw)
        logger.info(f"Started discharging at {abs(power_kw)}kW")
        
    async def _hold_position(self):
        """Hold current position (stop charging/discharging)"""
        self.current_power_kw = 0.0
        self.estimated_completion_time = None
        logger.info("Holding position - stopped charging/discharging")
        
    async def _enable_auto_mode(self):
        """Enable automatic mode"""
        self.mode = ControlMode.AUTOMATIC
        self.current_power_kw = 0.0  # Let ML system take control
        self.estimated_completion_time = None
        logger.info("Enabled automatic mode")
        
    def _estimate_completion(self, action: ControlAction) -> Optional[str]:
        """Estimate when command will complete"""
        return estimate_completion(action, self.current_soc, self.battery_capacity_kwh)
        
    def _calculate_charge_completion_time(self, power_kw: float) -> Optional[datetime]:
        """Calculate when charging will complete"""
        return calculate_charge_completion_time(
            self.current_soc,
            self.battery_capacity_kwh,
            power_kw,
        )
        
    def _calculate_discharge_completion_time(self, power_kw: float) -> Optional[datetime]:
        """Calculate when discharging will complete"""
        return calculate_discharge_completion_time(
            self.current_soc,
            self.battery_capacity_kwh,
            power_kw,
        )
        
    async def _save_status(self):
        """Save current status to file for persistence"""
        status_data = build_persisted_status_data(
            self.get_status(),
            self.get_command_history(20),
            self.scheduled_commands,
        )
        
        try:
            with open(self.status_file, 'w') as f:
                json.dump(status_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save status: {e}")

# Global controller instance
_controller_instance = None

def get_controller() -> VirtualInverterController:
    """Get global controller instance (singleton pattern)"""
    global _controller_instance
    if _controller_instance is None:
        _controller_instance = VirtualInverterController()
    return _controller_instance

def reset_controller():
    """Reset controller instance (for testing)"""
    global _controller_instance
    _controller_instance = None