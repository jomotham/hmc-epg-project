from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QKeyEvent

class TextEdit(QTextEdit):
    """ allow shift+enter to create new line in text edit """
    returnPressed = pyqtSignal()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                # shift+enter creates new line
                super().keyPressEvent(event)
            else:
                # if just enter, emit custom signal
                self.returnPressed.emit()
        elif event.key() == Qt.Key.Key_Tab:
            event.ignore()

            # add functionality with tab
        else:
            super().keyPressEvent(event)