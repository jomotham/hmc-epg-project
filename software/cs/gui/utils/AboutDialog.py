from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QDialogButtonBox
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About SCIDO")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        # Logo
        logo = QLabel()
        pixmap = QPixmap("SCIDO.png").scaledToWidth(180, Qt.TransformationMode.SmoothTransformation)
        logo.setPixmap(pixmap)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo)

        # Info text
        info = QLabel(
            "<h2>SCIDO</h2>"
            "<h4>Supervised Classification of Insect Data & Observations</h4>"
            "<p><b>Version:</b> 0.1.4<br>"
            "<b>Last Update Release:</b> Aug 29, 2025<br>"
        )
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setWordWrap(True)
        layout.addWidget(info)

        # Close button
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
