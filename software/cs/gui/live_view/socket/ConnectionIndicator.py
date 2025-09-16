from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QSizePolicy
from PyQt6.QtCore import Qt

class ConnectionIndicator(QWidget):
    def __init__(self):
        super().__init__()

        self.text_label = QLabel()
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        self.indicator = QLabel()
        self.indicator.setFixedSize(15,15)
        self.indicator.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.set_connected(False)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.indicator)
        layout.addWidget(self.text_label)

        self.setLayout(layout)

    def set_connected(self, connected: bool):
        """
        Updates the indicator color and label text based on connection status.
        """
        if connected:
            self.indicator.setStyleSheet("""
                background-color: #00CC66;  /* green */
                border: 0px solid #AAAAAA;
                border-radius: 7px;
            """)
            self.text_label.setText("ENGR Connected")
        else:
            self.indicator.setStyleSheet("""
                background-color: #CC0044;  /* red */
                border: 0px solid #AAAAAA;
                border-radius: 7px;
            """)
            self.text_label.setText("ENGR Disconnected")


