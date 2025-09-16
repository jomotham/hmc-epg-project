from PyQt6.QtWidgets import (
    QApplication, QWidget, QDialog, QLabel, QLineEdit, QDoubleSpinBox, QSpinBox,
    QComboBox, QPushButton, QHBoxLayout, QVBoxLayout, QFormLayout, QDialogButtonBox,
    QSpacerItem, QSizePolicy, QToolButton, QFileDialog
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QSize
import sys
import os

from settings import settings


class NewRecordingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Create New EPG Recording")
        self.setMinimumWidth(500)
        self.setModal(True)

        # === Input Fields ===
        self.filename_edit = QLineEdit()
        self.filename_edit.setPlaceholderText("Untitled recording")
        self.filename_edit.setMinimumWidth(250)

        spacer = QSpacerItem(0, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        # --- Voltage Range Inputs ---
        voltage_layout = QHBoxLayout()
        voltage_layout.setContentsMargins(0, 0, 0, 0)  # Remove padding
        voltage_layout.setSpacing(8)

        self.voltage_min_spin = QDoubleSpinBox()
        self.voltage_min_spin.setRange(-1000, 0)
        self.voltage_min_spin.setSuffix(" V")
        self.voltage_min_spin.setSingleStep(0.1)
        self.voltage_min_spin.setDecimals(2)
        self.voltage_min_spin.setValue(-0.5)

        self.voltage_max_spin = QDoubleSpinBox()
        self.voltage_max_spin.setRange(0, 1000)
        self.voltage_max_spin.setSuffix(" V")
        self.voltage_max_spin.setSingleStep(0.1)
        self.voltage_max_spin.setDecimals(2)
        self.voltage_max_spin.setValue(1.0)

        voltage_layout.addWidget(QLabel("Min:"))
        voltage_layout.addWidget(self.voltage_min_spin)
        voltage_layout.addSpacing(10)
        voltage_layout.addWidget(QLabel("Max:"))
        voltage_layout.addWidget(self.voltage_max_spin)

        voltage_widget = QWidget()
        voltage_widget.setLayout(voltage_layout)

        # voltage_info_icon = QToolButton()
        # voltage_info_icon.setIcon(QIcon("icons/info-circle.svg"))
        # voltage_info_icon.setIconSize(QSize(16, 16))     # size of the icon inside the button
        # voltage_info_icon.setFixedSize(24, 24)           # size of the button itself
        # voltage_info_icon.setToolTip("Info tooltip here")
        # voltage_info_icon.setStyleSheet("QToolButton { border: none; padding: 4px; }")


        # voltage_info_button = QToolButton()
        # voltage_info_button.setIcon(QIcon("icons/info-circle.svg"))
        # voltage_info_button.setIconSize(QSize(16, 16))
        # voltage_info_button.setToolTip("Sets the initial visible voltage range.\nDoes not affect the data.")
        # voltage_info_button.setStyleSheet("""
        #     QToolButton {
        #         border: none;
        #         padding: 4px;
        #         color: white;
        #     }                          
        # """)
        # voltage_info_button.setFixedSize(24, 24)
        # voltage_info_button.setCursor(Qt.CursorShape.WhatsThisCursor)

        
        info_row = QHBoxLayout()
        info_row.addWidget(voltage_widget)
        # info_row.addWidget(voltage_info_icon,alignment=Qt.AlignmentFlag.AlignVCenter)

        wrapper = QWidget()
        wrapper.setLayout(info_row)

        # === Layouts ===
        form_layout = QFormLayout()
        form_layout.setHorizontalSpacing(30)
        form_layout.addRow("Filename", self.filename_edit)
        form_layout.addItem(spacer)
        form_layout.addRow("Initial Voltage Range", wrapper)
        # form_layout.addRow(voltage_info_label)
        # form_layout.addRow("Min Voltage:", self.min_voltage_spin)
        # form_layout.addRow(self.min_voltage_label)
        # form_layout.addRow("Max Voltage:", self.max_voltage_spin)
        # form_layout.addRow("Sampling Rate:", self.sampling_rate_spin)
        # form_layout.addRow("Duration:", self.duration_spin)
        # form_layout.addRow("Channels:", self.channel_combo)

        # === Buttons ===
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.prompt_save_location)
        self.button_box.rejected.connect(self.reject)

        # === Final Layout ===
        layout = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

        self.save_file_path = None

    def prompt_save_location(self):
        """
        Opens a file dialog to prompt the user for a save location
        """

        initial_filename = self.filename_edit.text().strip()

        if not initial_filename:
            initial_filename = "Untitled.csv"

        initial_path = os.path.join(settings.get("default_recording_directory"), initial_filename)

        # open file dialog
        save_path, _ = QFileDialog.getSaveFileName(
            parent=self,
            caption="Save As",
            directory=initial_path,
            filter="CSV Files (*.csv);;All Files (*)"
        )

        if save_path:
            self.save_file_path = save_path
            self.accept()
        else:
            self.save_file_path = None

    def get_data(self):
        return {
            "filename": self.save_file_path,
            "min_voltage": self.voltage_min_spin.value(),
            "max_voltage": self.voltage_max_spin.value(),
        }

def main():
    app = QApplication(sys.argv)
    dialog = NewRecordingDialog()
    if dialog.exec():
        data = dialog.get_data()
        print("Recording settings:")
        for key, value in data.items():
            print(f"  {key}: {value}")
    else:
        print("User cancelled.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
