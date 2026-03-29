import os
import socket
import logging
import sys
from app.daemon.protocol import parse_request, make_response
from app.daemon.handlers import dispatch_action
from app.utils.logger import get_logger

logger = get_logger(__name__)

SOCKET_PATH = "/tmp/commander_pro_control.sock"

def run_server():
    if os.getuid() != 0:
        logger.warning("Daemon is not running as root. Some liquidctl commands might fail.")

    # Clean up stale socket
    if os.path.exists(SOCKET_PATH):
        try:
            os.remove(SOCKET_PATH)
            logger.debug(f"Removed stale socket: {SOCKET_PATH}")
        except OSError as e:
            logger.error(f"Failed to remove stale socket {SOCKET_PATH}: {e}")
            sys.exit(1)

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    
    try:
        server.bind(SOCKET_PATH)
        # Allow any user on the system to connect to the socket, or just the user.
        # It's in /tmp, so it's readable. Let's make it accessible to everyone (0o666),
        # so unprivileged GUI clients can connect.
        os.chmod(SOCKET_PATH, 0o666)
    except Exception as e:
        logger.error(f"Failed to bind socket {SOCKET_PATH}: {e}")
        sys.exit(1)

    server.listen(5)
    logger.info(f"Daemon listening on {SOCKET_PATH}")

    try:
        while True:
            conn, addr = server.accept()
            with conn:
                # Basic reading line by line (assuming short JSON payloads)
                data = b""
                while True:
                    chunk = conn.recv(1024)
                    if not chunk:
                        break
                    data += chunk
                    if b"\n" in chunk:
                        break
                
                if not data:
                    continue
                    
                request = parse_request(data.decode('utf-8').strip())
                if not request:
                    logger.warning("Received invalid request data")
                    resp_str = make_response(False, "Invalid JSON or missing action.")
                    conn.sendall(resp_str.encode('utf-8'))
                    continue
                
                action = request["action"]
                payload = request["payload"]
                
                # Dispatch securely using the predefined handlers
                success, msg, resp_data = dispatch_action(action, payload)
                
                # Send response
                resp_str = make_response(success, msg, resp_data)
                conn.sendall(resp_str.encode('utf-8'))
                
    except KeyboardInterrupt:
        logger.info("Daemon stopping...")
    except Exception as e:
        logger.error(f"Daemon encountered a fatal error: {e}", exc_info=True)
    finally:
        server.close()
        if os.path.exists(SOCKET_PATH):
            os.remove(SOCKET_PATH)
            logger.info(f"Cleaned up socket {SOCKET_PATH}")

if __name__ == "__main__":
    run_server()
