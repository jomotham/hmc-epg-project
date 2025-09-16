from PyQt6.QtCore import pyqtSignal, QThread, QObject, QTimer

import subprocess
from winrt.windows.devices import radios


class BluetoothWorker(QObject):
    """
    Runs Bluetooth state checks in a background thread.
    Emits (has_adapter, enabled) via resultReady.
    """
    resultReady = pyqtSignal(bool, bool)  # (has_adapter, enabled)

    def check_bluetooth(self):
        """Check for a Bluetooth adapter and whether it is enabled."""
        result = subprocess.run(
            ["powershell", "-Command", "Get-PnpDevice -Class Bluetooth"],
            capture_output=True, text=True
        )
        has_adapter = bool(result.stdout.strip())
        if not has_adapter:
            self.resultReady.emit(False, False)
            return

        try:
            radios_list = radios.Radio.get_radios_async().get()
            for r in radios_list:
                if r.kind == radios.RadioKind.BLUETOOTH:
                    self.resultReady.emit(True, r.state == radios.RadioState.ON)
                    return
            self.resultReady.emit(True, False)
        except Exception:
            self.resultReady.emit(has_adapter, False)

class BluetoothManager(QObject):
    """
    Manages periodic Bluetooth checks with a worker thread.
    Emits stateChanged(has_adapter, enabled).
    """
    stateChanged = pyqtSignal(bool, bool)  # (has_adapter, enabled)

    def __init__(self, poll_interval_ms=2000, parent=None):
        """
        Args:
            poll_interval_ms: Interval in ms between checks.
        """
        super().__init__(parent)
        self.bt_thread = None
        self.bt_worker = None

        self.timer = QTimer(self)
        self.timer.setInterval(poll_interval_ms)
        self.timer.timeout.connect(self.update_status)
        self.timer.start()

        self.update_status()  # first check immediately

    def update_status(self):
        """Start a BluetoothWorker if no thread is running."""
        if self.bt_thread is not None and self.bt_thread.isRunning():
            return

        self.bt_thread = QThread()
        self.bt_worker = BluetoothWorker()
        self.bt_worker.moveToThread(self.bt_thread)

        self.bt_thread.started.connect(self.bt_worker.check_bluetooth)
        self.bt_worker.resultReady.connect(self.stateChanged)  # forward result
        self.bt_worker.resultReady.connect(self.bt_thread.quit)
        self.bt_worker.resultReady.connect(self.bt_worker.deleteLater)
        self.bt_thread.finished.connect(self.bt_thread.deleteLater)
        self.bt_thread.finished.connect(self._clear_thread_ref)

        self.bt_thread.start()

    def _clear_thread_ref(self):
        """Reset thread/worker references after finish."""
        self.bt_thread = None
        self.bt_worker = None

    @staticmethod
    def open_settings():
        """Open the Windows Bluetooth Settings panel."""
        subprocess.Popen(["start", "ms-settings:bluetooth"], shell=True)