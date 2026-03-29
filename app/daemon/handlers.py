from typing import Dict, Any, Callable, Tuple
from app.services.liquidctl_runner import LiquidctlRunner
from app.utils.logger import get_logger
from app.utils.validators import validate_fan_number, validate_fan_speed

logger = get_logger(__name__)

# The daemon will run as root, so it doesn't need to invoke sudo inside subprocess
runner = LiquidctlRunner(use_sudo=False)

def handle_initialize_all(payload: Dict[str, Any]) -> Tuple[bool, str, Any]:
    success, msg = runner.initialize_devices()
    return success, msg, None

def handle_get_status(payload: Dict[str, Any]) -> Tuple[bool, str, Any]:
    success, msg = runner.get_status()
    # If success, msg contains the stdout which is the status text
    if success:
        return True, "Status retrieved successfully.", {"status_text": msg}
    return False, msg, None

def handle_list_devices(payload: Dict[str, Any]) -> Tuple[bool, str, Any]:
    success, msg = runner.list_devices()
    if success:
        return True, "Devices listed successfully.", {"devices_text": msg}
    return False, msg, None

def handle_set_fixed_speed(payload: Dict[str, Any]) -> Tuple[bool, str, Any]:
    fan_id = payload.get("fan_id")
    speed = payload.get("speed")
    
    if fan_id is None or speed is None:
        return False, "Missing 'fan_id' or 'speed' in payload.", None
        
    try:
        fan_id_int = int(str(fan_id))
        speed_int = int(str(speed))
    except ValueError:
        return False, "Invalid type for 'fan_id' or 'speed', must be integers.", None
        
    if not validate_fan_number(fan_id_int):
        return False, f"Invalid fan number: {fan_id_int}", None
    if not validate_fan_speed(speed_int):
        return False, f"Invalid speed: {speed_int}", None
        
    success, msg = runner.set_fan_speed(fan_id_int, speed_int)
    return success, msg, None

# Map of supported actions to handler functions
ACTION_HANDLERS: Dict[str, Callable[[Dict[str, Any]], Tuple[bool, str, Any]]] = {
    "initialize_all": handle_initialize_all,
    "get_status": handle_get_status,
    "list_devices": handle_list_devices,
    "set_fixed_speed": handle_set_fixed_speed
}

def dispatch_action(action: str, payload: Dict[str, Any]) -> Tuple[bool, str, Any]:
    handler = ACTION_HANDLERS.get(action)
    if not handler:
        logger.warning(f"Unknown action requested: {action}")
        return False, f"Unknown action: {action}", None
        
    logger.info(f"Dispatching action: {action}")
    try:
        return handler(payload)
    except Exception as e:
        logger.error(f"Error handling action '{action}': {e}", exc_info=True)
        return False, f"Internal daemon error: {e}", None
