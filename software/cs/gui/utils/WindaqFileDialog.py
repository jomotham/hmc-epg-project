from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QDialogButtonBox, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
import os
import sys
import windaq as wdq

class WindaqFileDialog(QDialog):
    """
    A dialog for selecting a channel from a WinDAQ file.
    """
    def __init__(self, filepath: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select WinDAQ Channel")
        self.setMinimumWidth(500)
        self.setModal(True)

        # find list of winDAQ Channels
        daq = wdq.windaq(filepath)
        numOfChannels = len(daq._annotations)
        channel_annotations = [f"{x+1}: {daq.chAnnotation(x+1)}" for x in range(numOfChannels-1)]
        self.selected_channel_index = -1

        main_layout = QVBoxLayout(self)

        info_label = QLabel("Please select the channel you wish to load as 'Voltage':")
        main_layout.addWidget(info_label)

        channel_layout = QHBoxLayout()
        channel_label = QLabel("Channel:")
        self.channel_combo = QComboBox()
        self.channel_combo.addItems(channel_annotations) # Populate dropdown with channel names
        self.channel_combo.setCurrentIndex(0) # Select the first channel by default

        channel_layout.addWidget(channel_label)
        channel_layout.addWidget(self.channel_combo)
        main_layout.addLayout(channel_layout)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept_selection)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

    def accept_selection(self):
        """
        Stores the index of the selected channel and accepts the dialog.
        """
        self.selected_channel_index = self.channel_combo.currentIndex()
        self.accept()

    def get_selected_channel_index(self) -> int:
        """
        Returns the 1-based index of the channel selected by the user.
        """
        return self.selected_channel_index + 1

# --- For standalone testing (optional) ---
# if __name__ == "__main__":
#     app = QApplication(sys.argv)
    
#     # Example channel names you might get from a WinDAQ file
#     example_channels = ["Channel 1 (Pre-Rect)", "Channel 2 (Post-Rect)", "Channel 3 (Aux)"]
    
#     dialog = WindaqChannelSelectionDialog(example_channels)
    
#     if dialog.exec():
#         selected_index = dialog.get_selected_channel_index()
#         print(f"User selected channel index: {selected_index}")
#         print(f"Selected channel name: {example_channels[selected_index]}")
#     else:
#         print("User cancelled channel selection.")
        
#     sys.exit(app.exec())
