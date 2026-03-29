import sys
from PySide6.QtWidgets import QApplication
from app.ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    
    # Set application metadata
    app.setApplicationName("Commander Pro Control")
    app.setOrganizationName("CustomLinuxApps")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
