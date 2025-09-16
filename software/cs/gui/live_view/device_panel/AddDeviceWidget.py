from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QBrush, QColor, QPen
from utils.SVGIcon import svg_to_colored_pixmap


class AddDeviceWidget(QWidget):
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(50)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(12)

        # Plus icon
        self.icon_label = QLabel()
        self.icon_label.setPixmap(svg_to_colored_pixmap("icons/plus.svg", "#EBEBEB", 24))
        layout.addWidget(self.icon_label)

        # Text
        self.text_label = QLabel("Add new EPG device")
        self.text_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #EBEBEB;
            }
            QLabel:disabled {
                color: #777777;
            }
        """)
        layout.addWidget(self.text_label)

        layout.addStretch()

        self._hover = False

    def setEnabled(self, enabled: bool):
        super().setEnabled(enabled)
        if enabled:
            self.icon_label.setPixmap(svg_to_colored_pixmap("icons/plus.svg", "#EBEBEB", 24))
        else:
            self.icon_label.setPixmap(svg_to_colored_pixmap("icons/plus.svg", "#777777", 24))

    def enterEvent(self, event):
        if self.isEnabled():   # only respond if enabled
            self._hover = True
            self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.isEnabled():
            self._hover = False
            self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)

        if not self.isEnabled():
            brush = QBrush(QColor("#1E1E1E"))  # disabled background
        elif self._hover:
            brush = QBrush(QColor("#2F2F2F"))
        else:
            brush = QBrush(QColor("#1E1E1E"))

        pen = QPen(QColor("#666666"))  # grey outline
        painter.setPen(pen)
        painter.setBrush(brush)
        painter.drawRoundedRect(rect, 5, 5)

    def mousePressEvent(self, event):
        if self.isEnabled() and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
