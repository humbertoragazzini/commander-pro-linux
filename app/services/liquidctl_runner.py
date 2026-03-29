import subprocess
from typing import Optional, Tuple
from app.utils.logger import get_logger
from app.utils.validators import validate_fan_number, validate_fan_speed

logger = get_logger(__name__)

class LiquidctlRunner:
    """Service class to handle all liquidctl command execution."""
    
    def __init__(self, use_sudo: bool = True):
        self.use_sudo = use_sudo
        self.base_match = ["--match", "Commander Pro", "--pick", "0"]
        logger.info(f"LiquidctlRunner initialized (use_sudo={use_sudo})")

    def _run_command(self, cmd_args: list[str]) -> Tuple[bool, str]:
        """Runs the liquidctl command safely via subprocess."""
        cmd = []
        if self.use_sudo:
            cmd.extend(["sudo", "-n"]) # non-interactive sudo
            
        cmd.append("liquidctl")
        cmd.extend(cmd_args)
        
        cmd_str = " ".join(cmd)
        logger.debug(f"Executing: {cmd_str}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f"Command success: {cmd_str}")
            return True, result.stdout.strip()
        except subprocess.CalledProcessError as e:
            err_msg = e.stderr.strip() or e.stdout.strip() or str(e)
            logger.error(f"Command failed ({e.returncode}): {cmd_str} | Error: {err_msg}")
            return False, err_msg
        except FileNotFoundError:
            logger.error(f"Executable not found in path. Is liquidctl installed?")
            return False, "liquidctl not found."

    def initialize_devices(self) -> Tuple[bool, str]:
        """Runs: liquidctl initialize all"""
        return self._run_command(["initialize", "all"])

    def set_fan_speed(self, fan_number: int, speed: int) -> Tuple[bool, str]:
        """Runs: liquidctl --match 'Commander Pro' --pick 0 set fan<N> speed <SPEED>"""
        if not validate_fan_number(fan_number):
            return False, f"Invalid fan number: {fan_number}"
        if not validate_fan_speed(speed):
            return False, f"Invalid speed: {speed}"
        
        args = self.base_match + ["set", f"fan{fan_number}", "speed", str(speed)]
        return self._run_command(args)
