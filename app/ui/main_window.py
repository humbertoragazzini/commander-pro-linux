from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QGroupBox, QMessageBox, QScrollArea
)
from PySide6.QtCore import Qt

from app.ui.fan_widget import FanControlWidget
from app.services.daemon_client import DaemonClient
from app.models.preset import Preset
from app.config.settings import load_settings, save_settings, AppSettings
from app.utils.logger import get_logger

logger = get_logger(__name__)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Commander Pro Control")
        self.setMinimumWidth(400)
        self.setMinimumHeight(500)
        
        self.client = DaemonClient()
        self.settings = load_settings()
        self.fan_widgets: dict[int, FanControlWidget] = {}
        
        self._setup_ui()
        self._load_settings_to_ui()

    def _setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        layout = QVBoxLayout(main_widget)
        
        # --- Device Section ---
        dev_group = QGroupBox("Device Operations")
        dev_layout = QHBoxLayout()
        self.btn_init = QPushButton("Initialize Device")
        self.btn_init.clicked.connect(self.on_initialize)
        dev_layout.addWidget(self.btn_init)
        dev_group.setLayout(dev_layout)
        layout.addWidget(dev_group)
        
        # --- Fans Section ---
        fans_group = QGroupBox("Fan Control (1-6)")
        fans_layout = QVBoxLayout()
        
        for i in range(1, 7):
            fw = FanControlWidget(fan_id=i)
            self.fan_widgets[i] = fw
            fans_layout.addWidget(fw)
            
        fans_group.setLayout(fans_layout)
        layout.addWidget(fans_group)
        
        # --- Presets Section ---
        preset_group = QGroupBox("Presets")
        preset_layout = QHBoxLayout()
        
        btn_quiet = QPushButton("Quiet (30%)")
        btn_quiet.clicked.connect(lambda: self.apply_preset(Preset.QUIET.value))
        
        btn_balanced = QPushButton("Balanced (50%)")
        btn_balanced.clicked.connect(lambda: self.apply_preset(Preset.BALANCED.value))
        
        btn_perf = QPushButton("Performance (80%)")
        btn_perf.clicked.connect(lambda: self.apply_preset(Preset.PERFORMANCE.value))
        
        preset_layout.addWidget(btn_quiet)
        preset_layout.addWidget(btn_balanced)
        preset_layout.addWidget(btn_perf)
        preset_group.setLayout(preset_layout)
        layout.addWidget(preset_group)
        
        # --- Actions Section ---
        actions_layout = QHBoxLayout()
        self.btn_apply_all = QPushButton("Apply All Fans")
        self.btn_apply_all.setStyleSheet("font-weight: bold; padding: 10px;")
        self.btn_apply_all.clicked.connect(self.on_apply_all)
        
        self.btn_save = QPushButton("Save Settings")
        self.btn_save.clicked.connect(self.on_save_settings)
        
        actions_layout.addWidget(self.btn_apply_all)
        actions_layout.addWidget(self.btn_save)
        layout.addLayout(actions_layout)
        
        # --- Status Area ---
        self.status_label = QLabel("Ready.")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: gray;")
        layout.addWidget(self.status_label)
        layout.addStretch()

    def _load_settings_to_ui(self):
        for str_id, speed in self.settings.fan_speeds.items():
            fid = int(str_id)
            if fid in self.fan_widgets:
                self.fan_widgets[fid].set_speed(speed)

    def set_status(self, message: str, is_error: bool = False):
        self.status_label.setText(message)
        color = "red" if is_error else "green"
        self.status_label.setStyleSheet(f"color: {color};")
        logger.info(f"Status update: {message}")

    def on_initialize(self):
        self.set_status("Initializing device...")
        success, msg = self.client.initialize_devices()
        if success:
            self.set_status("Device initialized successfully.")
            QMessageBox.information(self, "Success", "Device initialized successfully.")
        else:
            self.set_status(f"Initialization failed: {msg}", is_error=True)
            QMessageBox.warning(self, "Error", f"Initialization failed:\n{msg}")

    def apply_preset(self, speed: int):
        for fw in self.fan_widgets.values():
            fw.set_speed(speed)
        self.set_status(f"Applied preset: {speed}% to all fans UI. Click 'Apply All' to send to device.")

    def on_apply_all(self):
        self.set_status("Applying fan speeds...")
        errors = []
        for fid, fw in self.fan_widgets.items():
            speed = fw.get_speed()
            success, msg = self.client.set_fan_speed(fid, speed)
            if not success:
                errors.append(f"Fan {fid}: {msg}")
                
        if errors:
            err_msg = "\n".join(errors)
            self.set_status("Error applying to some fans.", is_error=True)
            QMessageBox.warning(self, "Apply Errors", f"Some commands failed:\n{err_msg}")
        else:
            self.set_status("All fan speeds applied successfully.")

    def on_save_settings(self):
        speeds = {str(fid): fw.get_speed() for fid, fw in self.fan_widgets.items()}
        self.settings.fan_speeds = speeds
        # Default preset str is not heavily used right now, but we save current state
        save_settings(self.settings)
        self.set_status("Settings saved successfully.")
