import json
from typing import Any, Dict, Optional, TypedDict

class Request(TypedDict):
    """Shape of the incoming JSON request from the GUI."""
    action: str
    payload: Optional[Dict[str, Any]]

class Response(TypedDict):
    """Shape of the outgoing JSON response to the GUI."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]]

def parse_request(data: str) -> Optional[Request]:
    """Parse a JSON string into a Request object. Returns None if invalid."""
    try:
        req = json.loads(data)
        if not isinstance(req, dict) or "action" not in req:
            return None
        return {
            "action": str(req["action"]),
            "payload": req.get("payload") if isinstance(req.get("payload"), dict) else {}
        }
    except json.JSONDecodeError:
        return None

    if not isinstance(req, dict) or "action" not in req:
        return None
        
    action_val = str(req["action"])
    payload_val = req.get("payload")
    if not isinstance(payload_val, dict):
        payload_val = {}
        
    return {
        "action": action_val,
        "payload": payload_val
    }
def make_response(success: bool, message: str, data: Optional[Dict[str, Any]] = None) -> str:
    """Format a Response object into a JSON string."""
    resp: Response = {
        "success": success,
        "message": message,
        "data": data
    }
    return json.dumps(resp) + "\n"
