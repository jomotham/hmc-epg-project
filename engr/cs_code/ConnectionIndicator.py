from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QLabel, QSizePolicy, QHBoxLayout

class ConnectionIndicator(QWidget):
    """
    An labeled indicator of whether the ENGR client is connected through the socket to the CS client.
    Had to be put in this file to avoid weird import timing errors
    """
    def __init__(self):
        super().__init__()
        self.text_label = QLabel()
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        self.indicator = QLabel()
        self.indicator.setFixedSize(15,15)
        self.indicator.setStyleSheet("""
                background-color: #CC0044;  /* red */
                border-radius: 7px;
            """)
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
            self.indicator.setStyleSheet("background-color: #00CC66; border-radius: 7px;")
            self.text_label.setText("CS Connected")
        else:
            self.indicator.setStyleSheet("background-color: #CC0044; border-radius: 7px;")
            self.text_label.setText("CS Disconnected")