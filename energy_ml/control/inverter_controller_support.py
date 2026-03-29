from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


def _command_value(action: Any) -> Any:
    command = getattr(action, "command", None)
    return getattr(command, "value", command)


def validate_command(action: Any, current_soc: float, max_power_kw: float) -> Dict[str, Any]:
    """Validate a control action against power and SOC limits."""
    if abs(action.power_kw) > max_power_kw:
        return {
            "valid": False,
            "reason": f"Power {action.power_kw}kW exceeds limit {max_power_kw}kW",
        }

    command = _command_value(action)
    if command == "charge":
        if current_soc >= 0.95:
            return {
                "valid": False,
                "reason": "Battery SOC too high for charging (>=95%)",
            }
        if action.power_kw <= 0:
            return {
                "valid": False,
                "reason": "Charge power must be positive",
            }
    elif command == "discharge":
        if current_soc <= 0.05:
            return {
                "valid": False,
                "reason": "Battery SOC too low for discharging (<=5%)",
            }
        if action.power_kw >= 0:
            return {
                "valid": False,
                "reason": "Discharge power must be negative",
            }

    return {"valid": True, "reason": "Command validated"}


def build_command_log(action: Any, current_soc: float, current_power_kw: float) -> Dict[str, Any]:
    """Create the pre-execution log payload for a control action."""
    return {
        "timestamp": action.timestamp.isoformat(),
        "command": _command_value(action),
        "power_kw": action.power_kw,
        "reason": action.reason,
        "user_id": action.user_id,
        "soc_before": current_soc,
        "power_before": current_power_kw,
    }


def append_command_result(
    command_log: Dict[str, Any],
    current_soc: float,
    current_power_kw: float,
    estimated_completion: Optional[str],
) -> Dict[str, Any]:
    """Add post-execution state to a command log payload."""
    command_log.update(
        {
            "soc_after": current_soc,
            "power_after": current_power_kw,
            "estimated_completion": estimated_completion,
        }
    )
    return command_log


def trim_command_history(command_history: List[Dict[str, Any]], limit: int = 100) -> List[Dict[str, Any]]:
    """Cap in-memory command history to the newest entries."""
    if len(command_history) <= limit:
        return command_history
    return command_history[-limit:]


def build_schedule_entry(
    action: Any,
    scheduled_time: datetime,
    schedule_index: int,
    created_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Create a persisted scheduled-command record."""
    created_at = created_at or datetime.now()
    return {
        "id": f"sched_{schedule_index}_{int(scheduled_time.timestamp())}",
        "action": action.to_dict(),
        "scheduled_time": scheduled_time.isoformat(),
        "created_at": created_at.isoformat(),
        "status": "pending",
    }


def retain_recent_scheduled_commands(
    scheduled_commands: List[Dict[str, Any]],
    now: datetime,
    retention_hours: int = 24,
) -> List[Dict[str, Any]]:
    """Keep pending commands and recently executed historical entries."""
    cutoff_time = now - timedelta(hours=retention_hours)
    retained_commands = []
    for command in scheduled_commands:
        if command["status"] == "pending":
            retained_commands.append(command)
            continue

        effective_time = command.get("executed_at", command["created_at"])
        if datetime.fromisoformat(effective_time) > cutoff_time:
            retained_commands.append(command)

    return retained_commands


def pending_command_count(scheduled_commands: List[Dict[str, Any]]) -> int:
    """Count pending scheduled commands."""
    return len([command for command in scheduled_commands if command["status"] == "pending"])


def build_status_payload(
    *,
    current_soc: float,
    current_power_kw: float,
    mode_value: str,
    active_command: Any,
    battery_capacity_kwh: float,
    max_power_kw: float,
    estimated_completion_time: Optional[datetime],
    scheduled_commands: List[Dict[str, Any]],
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Serialize the current controller state for APIs and persistence."""
    now = now or datetime.now()
    return {
        "soc": round(current_soc * 100, 1),
        "power_kw": current_power_kw,
        "mode": mode_value,
        "active_command": _command_value(active_command) if active_command else None,
        "command_reason": active_command.reason if active_command else None,
        "battery_capacity_kwh": battery_capacity_kwh,
        "max_power_kw": max_power_kw,
        "last_update": now.isoformat(),
        "estimated_completion": estimated_completion_time.isoformat() if estimated_completion_time else None,
        "scheduled_commands_count": pending_command_count(scheduled_commands),
    }


def estimate_completion(
    action: Any,
    current_soc: float,
    battery_capacity_kwh: float,
    now: Optional[datetime] = None,
) -> Optional[str]:
    """Estimate completion time for the requested control action."""
    now = now or datetime.now()
    if action.duration_minutes:
        return (now + timedelta(minutes=action.duration_minutes)).isoformat()

    command = _command_value(action)
    if command == "charge" and action.power_kw > 0:
        remaining_capacity = (0.9 - current_soc) * battery_capacity_kwh
        hours_to_complete = remaining_capacity / action.power_kw
        return (now + timedelta(hours=hours_to_complete)).isoformat()

    if command == "discharge" and action.power_kw < 0:
        available_capacity = (current_soc - 0.1) * battery_capacity_kwh
        hours_to_complete = available_capacity / abs(action.power_kw)
        return (now + timedelta(hours=hours_to_complete)).isoformat()

    return None


def calculate_charge_completion_time(
    current_soc: float,
    battery_capacity_kwh: float,
    power_kw: float,
    now: Optional[datetime] = None,
) -> Optional[datetime]:
    """Calculate the datetime when charging should reach the target SOC."""
    if power_kw <= 0:
        return None

    now = now or datetime.now()
    remaining_capacity = (0.9 - current_soc) * battery_capacity_kwh
    hours_to_complete = remaining_capacity / power_kw
    return now + timedelta(hours=hours_to_complete)


def calculate_discharge_completion_time(
    current_soc: float,
    battery_capacity_kwh: float,
    power_kw: float,
    now: Optional[datetime] = None,
) -> Optional[datetime]:
    """Calculate the datetime when discharging should reach the target SOC."""
    if power_kw >= 0:
        return None

    now = now or datetime.now()
    available_capacity = (current_soc - 0.1) * battery_capacity_kwh
    hours_to_complete = available_capacity / abs(power_kw)
    return now + timedelta(hours=hours_to_complete)


def build_persisted_status_data(
    system_status: Dict[str, Any],
    command_history: List[Dict[str, Any]],
    scheduled_commands: List[Dict[str, Any]],
    saved_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Build the on-disk status payload."""
    saved_at = saved_at or datetime.now()
    return {
        "system_status": system_status,
        "command_history": command_history,
        "scheduled_commands": scheduled_commands,
        "last_saved": saved_at.isoformat(),
    }