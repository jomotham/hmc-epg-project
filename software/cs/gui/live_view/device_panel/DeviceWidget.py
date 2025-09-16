from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QToolButton, 
    QMenu, QInputDialog, QMessageBox, QDialog, QLineEdit, 
    QDialogButtonBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QAction, QIcon, QPainter, QBrush, QColor, QPen

import os
import re
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), r"..\..")))

from utils.SVGIcon import svg_to_colored_pixmap

class DeviceWidget(QWidget):
    connectRequested = pyqtSignal(str)  # emitted when clicked (mac address)
    editRequested = pyqtSignal(str)     # emitted when "Edit name" clicked
    macEditRequested = pyqtSignal(str)  # emitted when "Edit MAC" clicked
    forgetRequested = pyqtSignal(str)   # emitted when "Forget device" clic

    def __init__(self, mac: str, name: str | None = None, status: str = "Disconnected", parent=None):
        super().__init__(parent)

        self.mac = mac
        self.name = name or mac
        self.status = status
        self.setFixedHeight(70)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # --- Layout ---
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 6, 12, 6)
        main_layout.setSpacing(12)

        # PCB Icon 
        self.icon_label = QLabel()
        self.icon_label.setPixmap(svg_to_colored_pixmap("icons/circuit-board.svg", "#EBEBEB", 40))
        main_layout.addWidget(self.icon_label)

        # Device info (name + status)
        self.info_label = QLabel()
        self.info_label.setText(f"""
            <div style="text-align:left;">
                <div style="font-weight:bold; font-size:14px;">{self.name}</div>
                <div style="color:gray; font-size:12px;">{self.status}</div>
            </div>
        """)
        self.info_label.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.info_label)

        main_layout.addStretch()

        # Edit button with dropdown menu
        self.edit_button = QToolButton()
        icon_pixmap = svg_to_colored_pixmap("icons/edit.svg", "white", 30) 
        self.edit_button.setIcon(QIcon(icon_pixmap))
        self.edit_button.setIconSize(QSize(24, 24))
        self.edit_button.setToolTip("Edit this device")
        self.edit_button.setAutoRaise(True)
        main_layout.addWidget(self.edit_button)

        self.menu = QMenu(self)
        self.action_edit_name = QAction("Edit name", self)
        self.action_edit_mac = QAction("Edit MAC address", self)
        self.action_forget = QAction("Forget device", self)
        self.menu.addAction(self.action_edit_name)
        self.menu.addAction(self.action_edit_mac)
        self.menu.addSeparator()
        self.menu.addAction(self.action_forget)
        self.edit_button.setMenu(self.menu)
        self.edit_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        # Connect menu actions
        self.action_edit_name.triggered.connect(self.edit_name_dialog)
        self.action_edit_mac.triggered.connect(self.edit_mac_dialog)
        self.action_forget.triggered.connect(self.confirm_forget)

        # Hover state
        self._hover = False

    def enterEvent(self, event):
        if self.isEnabled():   # only allow hover if enabled
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
        radius = 5

        if not self.isEnabled():
            brush = QBrush(QColor("#1E1E1E"))  # fixed disabled background
        elif self._hover:
            brush = QBrush(QColor("#2F2F2F"))
        else:
            brush = QBrush(QColor("#1E1E1E"))

        pen = QPen(QColor("#888888"))
        painter.setPen(pen)
        painter.setBrush(brush)
        painter.drawRoundedRect(rect, radius, radius)

        super().paintEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.connectRequested.emit(self.mac)
        super().mousePressEvent(event)

    def update_info_label(self):
        self.info_label.setText(f"""
            <div style="text-align:left;">
                <div style="font-weight:bold; font-size:14px;">{self.name}</div>
                <div style="color:gray; font-size:12px;">{self.status}</div>
            </div>
        """)

    def set_status(self, status: str):
        self.status = status
        self.update_info_label()

    def set_name(self, name: str):
        self.name = name
        self.update_info_label()

    def edit_name_dialog(self):
        text, ok = QInputDialog.getText(self, "Edit Device Name", "Enter new name:", text=self.name)
        if ok and text.strip():
            self.set_name(text.strip())
            self.editRequested.emit(self.mac)  # notify panel

    def edit_mac_dialog(self):
        dlg = MacInputDialog(self.mac, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            old_mac = self.mac
            self.mac = dlg.get_mac()
            self.macEditRequested.emit(old_mac)  # notify DevicePanel
            self.update_info_label()
            
    def confirm_forget(self):
        reply = QMessageBox.question(
            self,
            "Forget Device",
            f"Are you sure you want to forget device:\n\n{self.name} ({self.mac})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.forgetRequested.emit(self.mac)

class MacInputDialog(QDialog):
    def __init__(self, current_mac: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit MAC Address")

        layout = QVBoxLayout(self)

        # Label above the input
        self.label = QLabel("Enter new MAC address:")
        layout.addWidget(self.label)

        # Text field
        self.mac_input = QLineEdit(current_mac)
        self.mac_input.setPlaceholderText("AA:BB:CC:DD:EE:FF")
        layout.addWidget(self.mac_input)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self):
        mac = self.mac_input.text().strip()
        if not is_valid_mac(mac):
            QMessageBox.warning(
                self, "Invalid MAC",
                "Please enter a valid MAC address (format: AA:BB:CC:DD:EE:FF)."
            )
            return  # keep dialog open
        super().accept()

    def get_mac(self) -> str:
        return self.mac_input.text().strip().upper()

    def get_mac(self) -> str:
        return self.mac_input.text().strip().upper()

def is_valid_mac(addr: str) -> bool:
    pattern = re.compile(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")
    return bool(pattern.match(addr.strip()))