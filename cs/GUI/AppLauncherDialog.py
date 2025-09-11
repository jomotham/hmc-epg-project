from PyQt6.QtWidgets import QApplication, QDialog, QHBoxLayout, QDialogButtonBox, QPushButton
import sys

# Import both your dialog and main window classes
from NewRecordingDialog import NewRecordingDialog
from utils.UploadFileDialog import UploadFileDialog
from main import main
from settings.SettingsWindow import SettingsWindow
from PyQt6.QtWidgets import QApplication, QDialog, QHBoxLayout, QPushButton, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal
import sys

class AppLauncherDialog(QDialog):
    launchMainWindowSettings = pyqtSignal(dict)
    launchMainWindowFile = pyqtSignal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SCIDO Launcher")
        self.setFixedSize(500, 250)

        main_layout = QVBoxLayout(self) # Set main layout for the dialog

        # Add a welcoming label
        welcome_label = QLabel("Welcome to SCIDO!\nChoose an action:")
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(welcome_label)

        button_layout = QHBoxLayout() # Layout for the buttons

        self.settings_button = QPushButton("Settings")
        self.settings_button.setMinimumHeight(40)
        self.settings_button.clicked.connect(self.open_settings_dialog)
        button_layout.addWidget(self.settings_button)

        self.new_recording_button = QPushButton("New Recording")
        self.new_recording_button.setMinimumHeight(40)
        self.new_recording_button.clicked.connect(self.open_new_recording_dialog)
        button_layout.addWidget(self.new_recording_button)

        self.upload_button = QPushButton("Upload File")
        self.upload_button.setMinimumHeight(40)
        self.upload_button.clicked.connect(self.open_upload_dialog)
        button_layout.addWidget(self.upload_button)

        main_layout.addLayout(button_layout)

        # Add a simple exit button for convenience if user doesn't want to proceed
        exit_button = QPushButton("Exit")
        exit_button.clicked.connect(self.reject) # Rejecting the dialog will close it
        main_layout.addWidget(exit_button, alignment=Qt.AlignmentFlag.AlignRight)

    def open_settings_dialog(self):
        # need to work on settings dialog
        settings_window = SettingsWindow(self)
        settings_window.setWindowFlag(Qt.WindowType.Window, True)
        settings_window.setWindowModality(Qt.WindowModality.WindowModal)
        settings_window.show()        # becomes visible
        settings_window.raise_()      # put at top of stacking order
        settings_window.activateWindow()

    def open_new_recording_dialog(self):
        new_recording_dialog = NewRecordingDialog()
        if new_recording_dialog.exec(): # open modally
            recording_settings = new_recording_dialog.get_data()
            self.launchMainWindowSettings.emit(recording_settings)
            self.accept() # Accept and close the AppLauncherDialog

    def open_upload_dialog(self):
        upload_dialog = UploadFileDialog()
        if upload_dialog.exec(): # open modally
            upload_file_path = upload_dialog.get_file_path()
            channel_idx = upload_dialog.get_channel_index()
            self.launchMainWindowFile.emit(upload_file_path, channel_idx)
            self.accept() # Accept and close the AppLauncherDialog

def launch_application():
    app = QApplication(sys.argv)
    launcher_dialog = AppLauncherDialog()

    main_window_instance = None

    def launch_main_window_with_settings(settings):
        nonlocal main_window_instance

        main_window_instance = main(app, recording_settings=settings)
        launcher_dialog.accept() 

    def launch_main_window_with_file(file, channel_index):
        nonlocal main_window_instance

        main_window_instance = main(app, file=file, channel_index=channel_index)
        launcher_dialog.accept() 

    launcher_dialog.launchMainWindowSettings.connect(launch_main_window_with_settings)
    launcher_dialog.launchMainWindowFile.connect(launch_main_window_with_file)

    result = launcher_dialog.exec()

    if result == QDialog.DialogCode.Accepted:
        pass
    else:
        sys.exit(0)

    sys.exit(app.exec())

if __name__ == "__main__":
    launch_application()

    