from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QSlider, QSpinBox
)
from PySide6.QtCore import Qt, Signal

class FanControlWidget(QWidget):
    speed_changed = Signal(int, int) # fan_id, new_speed

    def __init__(self, fan_id: int, initial_speed: int = 50, parent=None):
        super().__init__(parent)
        self.fan_id = fan_id
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Label
        self.label = QLabel(f"Fan {self.fan_id}:")
        self.label.setMinimumWidth(50)
        
        # Slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(initial_speed)
        
        # Spinbox
        self.spinbox = QSpinBox()
        self.spinbox.setRange(0, 100)
        self.spinbox.setValue(initial_speed)
        self.spinbox.setSuffix(" %")
        
        # Connect slider and spinbox to keep in sync
        self.slider.valueChanged.connect(self.spinbox.setValue)
        self.spinbox.valueChanged.connect(self.slider.setValue)
        
        # Emit signal when value changes
        self.slider.valueChanged.connect(self._on_value_changed)
        
        layout.addWidget(self.label)
        layout.addWidget(self.slider)
        layout.addWidget(self.spinbox)
        
    def _on_value_changed(self, value: int):
        self.speed_changed.emit(self.fan_id, value)

    def set_speed(self, speed: int):
        self.slider.setValue(speed)

    def get_speed(self) -> int:
        return self.slider.value()
