import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt
from typing import Dict, List, Tuple
import datetime

# Distinct colors for 6 fans (R, G, B)
FAN_COLORS = [
    (255, 99, 132),   # Fan 1: Red-ish
    (54, 162, 235),   # Fan 2: Blue-ish
    (255, 206, 86),   # Fan 3: Yellow-ish
    (75, 192, 192),   # Fan 4: Teal-ish
    (153, 102, 255),  # Fan 5: Purple-ish
    (255, 159, 64)    # Fan 6: Orange-ish
]

class FanSpeedGraphWidget(QWidget):
    """
    A reusable pyqtgraph widget designed to plot scrolling line charts for 6 fans.
    Maintains a bounded history buffer.
    """
    def __init__(self, history_size: int = 60, parent=None):
        super().__init__(parent)
        self.history_size = history_size
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Configure PyQtGraph globally to match standard UI themes
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        pg.setConfigOptions(antialias=True)
        
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setTitle("Live Fan Speed Monitoring")
        self.plot_widget.setLabel("left", "Speed (RPM or %)")
        self.plot_widget.setLabel("bottom", "Time (seconds ago)")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.addLegend(offset=(10, 10))
        
        # Invert X axis so 0 (now) is on the right, and historical data goes to the left (-time)
        # We'll plot X from e.g., -60 to 0
        self.plot_widget.setXRange(-self.history_size, 0)
        
        layout.addWidget(self.plot_widget)
        
        # Data storage structure: Fan ID (1-6) -> List of Tuple[Timestamp, Speed]
        self.history_data: Dict[int, List[Tuple[float, int]]] = {i: [] for i in range(1, 7)}
        
        # Line objects for updating
        self.lines: Dict[int, pg.PlotDataItem] = {}
        for i in range(1, 7):
            pen = pg.mkPen(color=FAN_COLORS[i-1], width=2)
            self.lines[i] = self.plot_widget.plot(name=f"Fan {i}", pen=pen)

    def set_buffer_size(self, size: int):
        self.history_size = size
        self.plot_widget.setXRange(-self.history_size, 0)
        
    def add_data_points(self, fan_speeds: Dict[int, int]):
        """
        Appends a snapshot of fan speeds mapping (1-6 -> int) at the current time.
        """
        now = datetime.datetime.now().timestamp()
        
        for fan_id, speed in fan_speeds.items():
            if fan_id in self.history_data:
                # Append new data
                self.history_data[fan_id].append((now, speed))
                
                # Trim to bounded size based on time (keep last N seconds roughly)
                # Or we can just bound the length of the list to self.history_size if polling is predictable.
                # Here we trim by array length to keep memory bounded simply.
                if len(self.history_data[fan_id]) > self.history_size:
                    self.history_data[fan_id].pop(0)

    def redraw_graph(self):
        """
        Redraws the plot lines to shift them visually with current time at X=0.
        """
        now = datetime.datetime.now().timestamp()
        
        max_y = 0
        
        for fan_id, data_points in self.history_data.items():
            if not data_points:
                continue
                
            x_values = []
            y_values = []
            
            for timestamp, speed in data_points:
                # X value is negative seconds ago
                seconds_ago = timestamp - now
                x_values.append(seconds_ago)
                y_values.append(speed)
                
                if speed > max_y:
                    max_y = speed
                    
            self.lines[fan_id].setData(x_values, y_values)
            
        # Optional dynamic auto-ranging for Y axis
        # Provide some padding above the highest speed
        if max_y > 0:
            self.plot_widget.setYRange(0, max_y * 1.1)
