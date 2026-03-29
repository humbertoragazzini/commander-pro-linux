import re
from typing import Dict
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Sample liquidctl output line: "├── Fan 1 speed               0  rpm"
# Or: "├── Fan 1 speed             800  rpm"
FAN_SPEED_REGEX = re.compile(r"Fan\s+(\d+)\s+speed.*?(\d+)\s+rpm", re.IGNORECASE)

def parse_status_output(output: str) -> Dict[int, int]:
    """
    Parses the raw text output from 'liquidctl status' to extract RPM values.
    Returns a dictionary mapping Fan ID (int) to its RPM speed (int).
    """
    fan_data: Dict[int, int] = {}
    
    if not output:
        return fan_data

    for line in output.splitlines():
        match = FAN_SPEED_REGEX.search(line)
        if match:
            try:
                fan_id = int(match.group(1))
                rpm = int(match.group(2))
                fan_data[fan_id] = rpm
            except ValueError:
                logger.warning(f"Failed to parse integers from regex match: {match.groups()}")
                
    return fan_data
