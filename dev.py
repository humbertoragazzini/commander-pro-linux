import os
import sys
import subprocess
import time

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    print("Please install watchdog: pip install watchdog")
    sys.exit(1)

class RestartHandler(FileSystemEventHandler):
    def __init__(self, cmd):
        self.cmd = cmd
        self.process = None
        self.restart()

    def restart(self):
        if self.process:
            print("[Dev] Detected change, restarting app...")
            self.process.terminate()
            self.process.wait()
        else:
            print("[Dev] Starting app...")
        
        self.process = subprocess.Popen(self.cmd)

    def on_any_event(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith('.py') or event.src_path.endswith('.json'):
            # Simple debounce could be added here if needed, 
            # but standard watchdog handles it okay for most edits.
            self.restart()

if __name__ == "__main__":
    app_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app")
    cmd = [sys.executable, "-m", "app.main"]
    
    event_handler = RestartHandler(cmd)
    observer = Observer()
    observer.schedule(event_handler, app_dir, recursive=True)
    observer.start()
    
    print(f"[Dev] Watching directory: {app_dir}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        if event_handler.process:
            event_handler.process.terminate()
    observer.join()
