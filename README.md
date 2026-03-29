# Commander Pro Control (Architecture & Study Guide)

Welcome to the **Commander Pro Control** project. This is a Linux desktop application for controlling Corsair Commander Pro fans using `liquidctl`. It is built with **Python 3** and **PySide6**. 

This `README` is more than just setup instructions. It serves as a comprehensive **study guide** to understand the application's internal architecture, specifically focusing on the privileged daemon and Inter-Process Communication (IPC) mechanism we use to keep the application secure and robust.

---

## 1. Project Overview

### What this App Does
This application provides a graphical interface (GUI) to view and control the fan speeds connected to a Corsair Commander Pro fan controller on Linux. It acts as a frontend for the `liquidctl` command-line utility.

### The Problem the Daemon Solves
By default, `liquidctl` requires superuser (`root`) privileges to interact with USB devices directly via the kernel/sysfs.
In earlier iterations, the GUI application itself either had to be run as `root` (e.g., `sudo python -m app.main`) or shell out to `sudo liquidctl...` directly from the user interface.

### Why calling `sudo` directly from the GUI is bad design
1. **Security Risk:** Running a massive framework like PySide6/Qt as root exposes a huge attack surface. A bug in the UI rendering engine could potentially compromise the entire system.
2. **User Experience:** If `sudo` requires a password, the `subprocess` call will unexpectedly block the GUI thread, freezing the app and preventing the user from entering their credentials, leading to broken timeouts.
3. **Coupling:** The graphical presentation layer should not be deeply tied to system administration commands.

### Why Daemon + IPC is safer and cleaner
To solve this, we split the app into two completely separate processes:
1. **The Daemon:** A small, headless Python script running as `root`. It lacks any UI dependencies, keeping it lean and secure. It is the *only* part of the project allowed to execute `liquidctl`.
2. **The GUI:** A PySide6 frontend running as your standard unprivileged Linux user. 

They communicate over an **IPC (Inter-Process Communication)** mechanism. The GUI asks the daemon to change a fan speed, and the daemon strictly validates that request before doing so.

---

## 2. High-Level Architecture

The project directory is structured categorically by roles:

*   **`app/daemon/`**: The core privileged backend. It listens to commands, verifies them, and calls the runner.
*   **`app/ui/`**: The unprivileged graphical interface. Draws buttons and sliders.
*   **`app/services/`**: Code that interacts with external processes (both the `liquidctl` binary and our own `daemon` socket).
*   **`app/models/`**: Simple data representations (e.g., Presets) that hold state.
*   **`app/utils/`**: Reusable helpers like structured logging and integer validation.
*   **`app/config/`**: Handles loading/saving user UI preferences to `~/.config/`.

**Request Flow (Plain English):**
When you click a button in the GUI (e.g., "Initialize Device"), the PySide6 button triggers a function. This function creates a Python dictionary (`{"action": "initialize_all"}`), converts it to text (JSON format), and pushes it into a local socket file `/tmp/commander_pro_control.sock`. The daemon, which is constantly listening to that file, reads the text, turns it back into a dictionary, checks if `"initialize_all"` is an approved action, and if so, runs the `liquidctl` command. It then sends a success message back through the socket, which the GUI reads to update the text on your screen.

---

## 3. Why Unix Domain Sockets Were Chosen

### What is a Unix Domain Socket?
A Unix domain socket (`AF_UNIX`) is a data communication endpoint for exchanging data between processes executing on the same host operating system. Unlike internet sockets (`AF_INET`) which use IP addresses and port numbers (like `127.0.0.1:8080`), Unix sockets use standard file paths (like `/tmp/commander_pro_control.sock`).

### Suitability for Local IPC on Linux
Unix sockets are significantly faster than networking sockets because they skip the entire network routing stack. They remain entirely in the kernel. Furthermore, since they are represented as files on the filesystem, we can use standard Linux file permissions (`chmod`, `chown`) to strictly control which users are allowed to talk to the daemon.

### Why not HTTP or arbitrary shell calls?
Using an HTTP web server (like Flask) internally just for a local desktop app is heavy and overkill. Arbitrary shell calls (GUI running `os.system("liquidctl...")`) bypass validation and invite shell injection attacks. Sockets provide a fast, secure, binary-safe, connection-oriented pipeline perfectly fitting our needs.

### How it is used in Dev Mode
During development, the socket is placed in `/tmp/commander_pro_control.sock` and granted liberal read/write permissions (`0o666`). This ensures that no matter what user you are testing the GUI as, it can reach the root daemon for testing purposes.

---

## 4. JSON Protocol Explanation

Data sent across the socket is formatted as JSON (JavaScript Object Notation).

**The Request Format:**
The GUI sends a single line of JSON to the daemon:
```json
{
  "action": "set_fixed_speed",
  "payload": {
    "fan_id": 1,
    "speed": 60
  }
}
```

**The Response Format:**
The daemon replies with a single line:
```json
{
  "success": true,
  "message": "liquidctl success output...",
  "data": null
}
```

**Action Mapping and Safety:**
The daemon uses the `"action"` string to route the command. It does not blindly execute anything provided in the payload. Instead, in `handlers.py`, `"set_fixed_speed"` translates specifically to `LiquidctlRunner.set_fan_speed(fan_id, speed)`. 
This is exponentially safer than allowing the GUI to pass raw terminal commands across the socket, because even if a malicious actor takes over the GUI process entirely, the absolute worst thing they can do is change your fan speeds. They cannot achieve a root shell.

---

## 5. Detailed File-By-File Explanation

### `app/daemon/server.py`
*   **What it does:** The lifecycle manager for the daemon. It creates the Unix socket, binds it to a file path, and enters an infinite `while True:` loop accepting connections.
*   **Why it exists:** We need a continuously running background script to receive socket requests.
*   **Key functions:** `run_server()`. It handles OS-level socket creation, permission setting, and chunked byte-reading (`client.recv(1024)`). Once it hits a newline character `\n`, it parses the JSON and dispatches it.

### `app/daemon/protocol.py`
*   **What it does:** Strict typing definitions and string parsing utilities for our JSON structure.
*   **Why it exists:** Keeps the raw JSON encode/decode logic abstracted away from the server logic.
*   **Key components:** the `Request` and `Response` type hints, `parse_request(string)`, and `make_response(bool, str, dict)`. 

### `app/daemon/handlers.py`
*   **What it does:** The security checkpoint. It maps acceptable action strings to executable functions. 
*   **Why it exists:** To validate input payloads securely before touching `subprocess`. 
*   **Key mechanisms:** It contains a dictionary `ACTION_HANDLERS` mapping strings like `"get_status"` to functions like `handle_get_status`. Inside `handle_set_fixed_speed`, it explicitly casts network data to integers and leverages strict integer bounds checking from `validators.py` before letting the command run.

### `app/services/liquidctl_runner.py`
*   **What it does:** A wrapper class `LiquidctlRunner` that directly interfaces with the `liquidctl` binary using Pythons `subprocess` module.
*   **Why it exists:** Abstracting terminal commands into Pythonic methods (`set_fan_speed(1, 50)` instead of `subprocess.run(["liquidctl", "set", "fan1", "speed", "50"])`). 
*   **Architecture shift:** Before, this was invoked by the GUI with `use_sudo=True`. Now, the daemon instantiates it with `use_sudo=False` because the daemon itself is already privileged.

### `app/services/daemon_client.py`
*   **What it does:** The GUI's counterpart to `server.py`. It connects to the socket, converts Python method calls to JSON requests, sends them, and waits for a response.
*   **Why it exists:** This prevents the UI code from being polluted with raw socket networking code. The UI just calls `client.set_fan_speed(1, 50)` and this class handles the network magic under the hood. It catches connection errors gracefully and returns tuples indicating success/failure.

### `app/utils/logger.py` & `app/utils/validators.py`
*   **What they do:** `logger.py` enforces a uniform console logging format across both Daemon and UI. `validators.py` is a single source of truth ensuring a fan ID is between 1-6 and speed is between 0-100.
*   **Architecture Role:** Both processes import these files, enabling code reuse and shared safety standards.

### `app/main.py` & `app/ui/main_window.py`
*   **What they do:** `main.py` bootstraps PySide6 (`QApplication`). `main_window.py` defines the actual desktop window, drawing fan sliders and preset buttons.
*   **Role in refactor:** `main_window.py` was heavily modified. We removed `LiquidctlRunner` and replaced it with `DaemonClient`. We added robust `QMessageBox` popups that display helpful errors if the daemon is unreachable, instead of the app completely crashing.

---

## 6. Library Explanation

Throughout the code, you will see standard and third-party libraries:

*   **`PySide6`**: The official Python binding for the Qt GUI framework. Used exclusively in the UI folder to draw native Linux windows and widgets.
*   **`subprocess`**: Used strictly by the `liquidctl_runner.py` to spawn the actual `liquidctl` terminal binary. 
*   **`socket`**: Used heavily in `server.py` and `daemon_client.py`. It is the low-level OS interface for IPC networking.
*   **`json`**: Used in `protocol.py` to serialize Python dictionaries into string bytes suitable for socket transmission.
*   **`os`**: Used for filesystem interaction, specifically checking if the socket file exists, deleting it (`os.remove`), and setting permissions (`os.chmod`).
*   **`typing`** (`Dict`, `Tuple`, `Optional`, `TypedDict`): Does not affect runtime behavior, but utilized heavily to help developers and IDE linters understand what data shapes functions expect, catching bugs before they happen.

---

## 7. Security Explanation Deep-Dive

**Moving execution into the Daemon:** 
The greatest improvement. If a malicious application interacts with your user desktop session or exploits the PySide6 app, it accesses an application running as a standard user. It cannot damage system files.

**Command Allowlisting:**
The daemon does not evaluate generic text strings. If it receives `"action": "format_hard_drive"`, `handlers.py` will log a warning and reject it because it is not in the hard-coded `ACTION_HANDLERS` dictionary. 

**Input Validation:**
If the GUI requests `"action": "set_fixed_speed", "payload": {"fan_id": "1; rm -rf /", "speed": 50}`, `handlers.py` attempts to cast `"1; rm -rf /"` to an Integer. This immediately throws a `ValueError` and the request is aborted. 

**Why `shell=False` Matters:**
In `liquidctl_runner.py`, `subprocess.run()` receives arguments as a Python List (`["liquidctl", "set", "fan1", "speed", "50"]`), not a single string. It does *not* invoke `/bin/sh` to parse the command. This means even if a malformed parameter slips past our integer validation, the OS kernel will interpret it literally as an argument to `liquidctl`, and never execute it as a rogue terminal command.

**Dev Scope constraints:**
Currently, `/tmp/commander_pro_control.sock` is set to `0o666` (readable/writable by anyone on the host machine). In development this is great, but in production, we would use system groups to restrict access to the socket file only to users in a specific `wheel` or `plugdev` group.

---

## 8. Development Mode Explanation

Because the daemon and UI are decoupled, you must start both manually to use the app from source code. This is intentionally designed to allow developers to read live logs in two separate terminals.

1. **Start the privileged daemon:**
   Open a terminal and run the background socket listener as root:
   ```bash
   sudo python3 -m app.daemon.server
   ```
   *You will see log lines showing the daemon waiting for connections.*

2. **Start the GUI client:**
   Open a second terminal and run the PySide6 app as a normal user:
   ```bash
   python3 -m app.main
   ```

If you start the GUI without the daemon running, the UI handles it perfectly. The `DaemonClient` catches the `FileNotFoundError` for the socket, returns a false state to the UI, and the UI gently tells you "Daemon is not running" in a status bar, rather than throwing a Python stack trace stack.

---

## 9. End-To-End Work Example

Let's dissect what happens when you drag the "Fan 1" slider to 80% and click "Apply All":

1. **[UI] `main_window.py`:** `on_apply_all()` iterates through all fan widgets, discovering Fan 1 is at 80%. It calls `self.client.set_fan_speed(1, 80)`.
2. **[Client] `daemon_client.py`:** Generates dictionary `{"action": "set_fixed_speed", "payload": {"fan_id": 1, "speed": 80}}`. It converts it to JSON text, opens `/tmp/commander_pro_control.sock`, and transmits the bytes.
3. **[Server] `server.py`:** Wakes up from `.accept()`, reads the bytes, splits by newlines, feeds it to `protocol.py`.
4. **[Daemon] `protocol.py`:** Verifies it is valid JSON and contains the `"action"` key.
5. **[Daemon] `handlers.py`:** Maps `"set_fixed_speed"` to `handle_set_fixed_speed()`. It extracts `1` and `80`. It runs `validate_fan_number(1)` and `validate_fan_speed(80)`. Both return True.
6. **[Runner] `liquidctl_runner.py`:** `runner.set_fan_speed(1, 80)` executes `subprocess.run(["liquidctl", "--match", "Commander Pro", "--pick", "0", "set", "fan1", "speed", "80"])`.
7. **[OS] Linux Kernel:** Changes the fan speed via USB. Returns stdout success to Python.
8. **[Daemon] `protocol.py`:** Wraps the success in internal `Response` format dictionary, serializes to JSON text, sends backward out the socket.
9. **[UI] `main_window.py`:** Receives the success tuple from the client, colors the bottom status bar green, and displays "All fan speeds applied successfully."

---

## 10. Future Improvements

With this robust dual-process architecture, several massive capabilities are unlocked:

*   **Background Polling & Fan Curves:** Because the daemon runs continuously, we could add a `QTimer` or standard threading loop inside the daemon to constantly query system temperatures. It could adjust fan speeds in the background entirely independent of the GUI. You could close the GUI, and your fans would still dynamically react to heat.
*   **Systemd Service:** The daemon can be easily wrapped in a `commander-pro.service` file to launch at boot by default without needing an active terminal window.
*   **Polkit Integration:** Instead of manual `sudo` terminal invocation, we could ship a `.policy` file allowing standard desktop launcher execution that prompts for elevated privileges visually just for the backend service startup.
*   **Tray Icon Integration:** PySide6's `QSystemTrayIcon` can be used to minimize the UI layer to the status bar, since the client/server connection isn't interrupted by a window being hidden. 

*Study this architecture well—decoupling privileged CLI interactions into validated sockets is an industry-standard mechanism for Linux desktop security!*
