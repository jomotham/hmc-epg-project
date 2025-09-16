# main.py
import sys
from PyQt6.QtWidgets import QApplication
from startup_loader import start_main_application

def main(app_instance, recording_settings=None, file=None, channel_index=None):
    return start_main_application(app_instance, recording_settings, file, channel_index)

if __name__ == "__main__":
    app = QApplication([])
    _ = main(app)
    sys.exit(app.exec())