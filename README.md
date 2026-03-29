# Commander Pro Control

A Linux desktop application for controlling Corsair Commander Pro fans using `liquidctl`.
Built with Python 3 and PySide6, designed to be modular and easy to expand.

## Architecture

The project is structured with a clean separation of concerns:

- **`models/`**: Simple data classes such as defaults and Presets.
- **`config/`**: Handles Loading and Saving of JSON user preferences to `~/.config/commander-pro-control/config.json`.
- **`utils/`**: Shared validation logic and a central console logger.
- **`services/`**: The core `liquidctl_runner.py` service and the newly added `daemon_client.py` for IPC. The UI no longer runs CLI commands directly and communicates via sockets.
- **`daemon/`**: The privileged python daemon that receives JSON commands over Unix domain sockets to securely execute `liquidctl` actions without giving the GUI sudo rights.
- **`ui/`**: PySide6 widgets. Broken down into the app window `main_window.py` and modular, reusable child components such as `fan_widget.py`. Let you easily append sensor readouts or new properties.
- **`main.py`**: PySide6 Application entrypoint. 

This layout cleanly separates business logic (services, models, config) from presentation logic (ui). Thus, expanding the app via headless systemd services or tray-icon equivalents utilizes the same core logic without coupling it tightly to window components. 

## Requirements

- Python 3.9+
- Provide working `liquidctl` utility in your system PATH (`sudo dnf install liquidctl` or `sudo apt install liquidctl` etc.)
- A working Corsair Commander Pro detected by `liquidctl` at `--pick 0`. 
- Sudo access. Setting `sudo -n` will work perfectly if NOPASSWD rules for `liquidctl` exist, else ensure you can run sudo.

## Installation

1. Clone or download the source code into a folder.
2. (Optional but recommended) Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## How to run the App (Development Mode)

Since the architecture is cleanly split between a privileged daemon and an unprivileged GUI, you must start both:

1. **Start the background daemon (needs root privileges):**
   ```bash
   sudo python3 -m app.daemon.server
   ```
   *The daemon listens on `/tmp/commander_pro_control.sock` and only allows strictly validated operations.*

2. **Start the unprivileged GUI (in a different terminal window):**
   ```bash
   python3 -m app.main
   ```

If the daemon is not running, the GUI will gracefully show connection errors instead of locking up.

## Suggestions for Next Improvements

1. **Systemd/Background Daemon**: Decouple the GUI process from polling the fans. A background Python daemon could control fan curves and expose a D-Bus interface or socket. The GUI can connect to it.
2. **Temperature based curves**: Expand the `FanControl` widget to have multiple modes ("Fixed Speed", "Curve"). Write a service task using `threading` or `QTimer` that periodically reads temps and adjust fan speeds based on a profile map inside `settings.py`.
3. **Tray Icon**: In PySide6, utilize `QSystemTrayIcon`. You can hide the `MainWindow` instead of closing it when pressing the exit button, enabling background curve control while hiding the UI. 
4. **Liquidctl Async Parsing**: If initializing or applying takes multiple seconds, it might freeze the PySide event loop. You could wrap `LiquidctlRunner` commands in a `QThread` and dispatch signals (`started`, `finished`, `error`) so the main thread (UI) remains snappy and can show loading spinners.
5. **Polkit Support**: Alternatively to `visudo`, `pkexec liquidctl ...` combined with a local `.policy` file installed in `/usr/share/polkit-1/actions/` is more standard for desktop linux apps instead of raw `sudo`. Or run `liquidctl` via group permissions/udev rules depending on backend kernel driver capabilities.
