import socket
import json
from typing import Tuple, Optional, Any, Dict
from app.utils.logger import get_logger
from app.utils.parsers import parse_status_output

logger = get_logger(__name__)

SOCKET_PATH = "/tmp/commander_pro_control.sock"

class DaemonClient:
    """Client for communicating with the Commander Pro daemon."""
    
    def __init__(self, socket_path: str = SOCKET_PATH):
        self.socket_path = socket_path

    def _send_request(self, action: str, payload: Optional[Dict[str, Any]] = None) -> Tuple[bool, str, Any]:
        """Sends a JSON request to the daemon socket and reads the response."""
        req: Dict[str, Any] = {
            "action": action,
            "payload": payload or {}
        }
        req_str = json.dumps(req) + "\n"
        
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.settimeout(5.0) # 5 seconds timeout
                client.connect(self.socket_path)
                client.sendall(req_str.encode('utf-8'))
                
                # Read response
                data = b""
                while True:
                    chunk = client.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                    if b"\n" in chunk:
                        break
                        
                if not data:
                    return False, "Received empty response from daemon.", None
                    
                resp = json.loads(data.decode('utf-8').strip())
                return resp.get("success", False), resp.get("message", "No message"), resp.get("data")
                
        except FileNotFoundError:
            logger.error(f"Daemon socket not found at {self.socket_path}. Is the daemon running?")
            return False, "Daemon socket not found. Make sure the daemon is running.", None
        except ConnectionRefusedError:
            logger.error(f"Connection refused to {self.socket_path}. Daemon might be down.")
            return False, "Connection refused. Make sure the daemon is running.", None
        except socket.timeout:
            logger.error(f"Timeout communicating with daemon.")
            return False, "Timeout waiting for daemon response.", None
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON response from daemon.")
            return False, "Invalid response from daemon.", None
        except Exception as e:
            logger.error(f"Unexpected error communicating with daemon: {e}", exc_info=True)
            return False, f"Communication error: {e}", None

    def initialize_devices(self) -> Tuple[bool, str]:
        """Requests the daemon to initialize the devices."""
        success, msg, _ = self._send_request("initialize_all")
        return success, msg

    def get_status(self) -> Tuple[bool, str, Dict[int, int]]:
        """Requests device status from daemon and parses fan RPMs."""
        success, msg, data = self._send_request("get_status")
        parsed_rpms = {}
        if success and data and "status_text" in data:
            parsed_rpms = parse_status_output(data["status_text"])
            return True, data["status_text"], parsed_rpms
        return success, msg, parsed_rpms

    def list_devices(self) -> Tuple[bool, str]:
        """Requests list of devices from daemon."""
        success, msg, data = self._send_request("list_devices")
        if success and data and "devices_text" in data:
            return True, data["devices_text"]
        return success, msg

    def set_fan_speed(self, fan_number: int, speed: int) -> Tuple[bool, str]:
        """Requests the daemon to set a fan speed."""
        payload = {"fan_id": fan_number, "speed": speed}
        success, msg, _ = self._send_request("set_fixed_speed", payload)
        return success, msg
