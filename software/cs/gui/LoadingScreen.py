from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QApplication
)
from PyQt6.QtGui import QPixmap, QFont
from PyQt6.QtCore import Qt

from utils.ResourcePath import resource_path

import sys


class LoadingScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SCIDO (loading)")
        center_point = QApplication.primaryScreen().availableGeometry().center()
        window_width = 800
        window_height = 400

        pos_x = center_point.x() - window_width // 2
        pos_y = center_point.y() - window_height // 2

        self.setFixedSize(window_width, window_height)
        self.move(pos_x, pos_y)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )

        left_widget = QWidget()
        left_widget.setStyleSheet("background-color: #1f2d40;")

        title = QLabel("SCIDO")
        title_font = QFont("Inter", 32, QFont.Weight.Bold, italic=True)
        title.setFont(title_font)
        title.setStyleSheet("color: #FFFEF9;")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)

        subtitle = QLabel("Supervised Classification of Insect Data & Observations")
        subtitle.setFont(QFont("Inter", 11, italic=True))
        subtitle.setStyleSheet("color: #FFFEF9;")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)

        loading = QLabel(" Loading...")
        loading.setFont(QFont("Inter", 12, italic=True))
        loading.setStyleSheet("color: #BBBAB9;")
        loading.setAlignment(Qt.AlignmentFlag.AlignLeft)

        version = QLabel("Version 0.1.5\nUSDA / Auburn University / Harvey Mudd College")
        version.setFont(QFont("Inter", 10))
        version.setStyleSheet("color: #FFFEF9;")
        version.setAlignment(Qt.AlignmentFlag.AlignLeft)

        logo = QLabel()
        img_path = resource_path("SCIDO.png")
        pixmap = QPixmap(img_path)
        logo.setPixmap(pixmap.scaledToHeight(300, Qt.TransformationMode.SmoothTransformation))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        left_widget = QWidget()
        left_widget.setStyleSheet("background-color: #1f2d40;")
        right_widget = QWidget()
        right_widget.setStyleSheet("background-color: #FFFEF9;")


        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(20,20,20,20)
        left_layout.addStretch()
        left_layout.addWidget(title)
        left_layout.addWidget(subtitle)
        left_layout.addStretch()
        left_layout.addWidget(loading)
        left_layout.addStretch()
        left_layout.addWidget(version)
        left_widget.setLayout(left_layout)

        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(20,0,20,0)
        right_layout.addStretch()
        right_layout.addWidget(logo, alignment=Qt.AlignmentFlag.AlignCenter)
        right_layout.addStretch()
        right_widget.setLayout(right_layout)


        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setSpacing(0)
        main_layout.addWidget(left_widget, 3) 
        main_layout.addWidget(right_widget,2)

        self.setLayout(main_layout)

def main():
    app = QApplication(sys.argv)
    win = LoadingScreen()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()