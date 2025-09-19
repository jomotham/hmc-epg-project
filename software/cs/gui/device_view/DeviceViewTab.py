import numpy as np
import os, sys
import time
from queue import Empty


from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QPushButton, QHBoxLayout, QVBoxLayout
)

from device_view.DeviceViewWindow import LiveDataWindow
from device_view.device_panel.DevicePanel import DevicePanel


class DeviceViewTab(QWidget):
    """NEEDS DOCSTRING?"""
    def __init__(self, recording_settings = None, parent=None):
        super().__init__(parent)

        self.initial_timestamp: float = None  # unix timestamp of the first data point in a recording
        self.total_pause_time: float = 0  # the cumulative length of any pauses
        self.pause_start_time: float = None # unix timestamp of the most recent pause


        self.datawindow = LiveDataWindow(parent=self)
        self.datawindow.getPlotItem().hideButtons()

        

        self.pause_live_button = QPushButton("Pause Live View", self)
        self.pause_live_button.setCheckable(True)
        self.pause_live_button.setChecked(True)
        self.pause_live_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pause_live_button.setStyleSheet("""
            QPushButton {
                background-color: #49a6fe;
                color: white;
                border-radius: 3px;
                padding: 5px;
                outline: none;
                width: 100px;
            } QPushButton:disabled {
                background-color: gray;
                color: white;
                border-radius: 3px;
                padding: 5px;
                outline: none;
            } QPushButton:focus {
                border: 3px solid #4aa8ff;
                padding: 2px;
            }
        """)

        self.add_comment_button = QPushButton("Add Comment", self)
        self.add_comment_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_comment_button.setToolTip("Add Comment at Current Time")
        self.add_comment_button.setStyleSheet("""
            QPushButton {
                background-color: #49a6fe;
                color: white;
                border-radius: 3px;
                padding: 5px;
                outline: none;
                width: 100px;
            } QPushButton:disabled {
                background-color: gray;
                color: white;
                border-radius: 3px;
                padding: 5px;
                outline: none;
            } QPushButton:focus {
                border: 3px solid #4aa8ff;
                padding: 2px;
            }
        """)
        self.add_comment_button.clicked.connect(self.call_add_comment)
        self.add_comment_button.setEnabled(False)
        
        self.pause_live_button.setCheckable(True)
        self.pause_live_button.setChecked(True)
        self.pause_live_button.setToolTip("Pause Live View")
        self.pause_live_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pause_live_button.clicked.connect(self.toggle_live)
        self.pause_live_button.setEnabled(False)
        


        

        # Reset zoom button (like in LabelViewTab)
        resetButton = QPushButton("Reset Zoom (R)")
        resetButton.setMinimumWidth(100)
        resetButton.clicked.connect(self.datawindow.reset_view)

        # Top layout (like in LabelViewTab)
        top_controls = QHBoxLayout()
        top_controls.addStretch(1)
        top_controls.addWidget(resetButton)

        top_controls_widget = QWidget()
        top_controls_widget.setLayout(top_controls)
        top_controls_widget.setStyleSheet("""
            QWidget {
                border-bottom: 1px solid #808080;
            }
        """)

        # Device panel (Windows only)
        if sys.platform.startswith("win"):
            self.device_panel = DevicePanel(parent=self)

        

        bottom_controls = QHBoxLayout()
        bottom_controls.addStretch()
        bottom_controls.addWidget(self.pause_live_button)
        bottom_controls.addWidget(self.add_comment_button)
        bottom_controls.addStretch()

        bottom_controls_widget = QWidget()
        bottom_controls_widget.setLayout(bottom_controls)
        bottom_controls_widget.setStyleSheet("""
            QWidget {
                border-top: 1px solid #808080;
            }
        """)

        center_layout = QVBoxLayout()
        center_layout.addWidget(top_controls_widget)
        center_layout.addWidget(self.datawindow)
        center_layout.addWidget(bottom_controls_widget)

        main_layout = QHBoxLayout()
        if sys.platform.startswith("win"):
            main_layout.addWidget(self.device_panel, 2)
        main_layout.addLayout(center_layout, 15)

        # can't figure out the 2 random tabs --> this logic below doesnt work either
        # self.setTabOrder(self.pause_live_button, self.add_comment_button)

        self.setLayout(main_layout)

    def toggleDevicePanel(self):
        if not self.device_button.isEnabled():
            return
        is_visible = self.device_panel.isVisible()
        self.device_panel.setVisible(not is_visible)     

    def toggle_live(self):
        live_mode = self.pause_live_button.isChecked()

        self.pause_live_button.setText("Pause Live View" if live_mode else "Resume Live View")
        self.datawindow.set_live_mode(live_mode)

    def call_add_comment(self):
        self.datawindow.add_comment_live()

    def start_recording(self):
        dw = self.datawindow
        dw.live_mode = True
        self.pause_live_button.setEnabled(True)
        self.pause_live_button.setToolTip("Pause Live View")
        self.add_comment_button.setEnabled(True)
        self.add_comment_button.setToolTip("Add Comment at Current Time")


        dw.xy_data = [np.array([]), np.array([])]
        dw.curve.clear()
        dw.scatter.clear()
        dw.buffer_data.clear()
        self.socket_client.recv_queue.queue.clear()

        self.initial_timestamp = time.time()
        dw.plot_update_timer.start()


    def pause_recording(self):
        dw = self.datawindow
        dw.plot_update_timer.stop()
        dw.live_mode = False

        self.pause_live_button.setEnabled(False)
        self.pause_live_button.setToolTip("Resume Recording to Toggle Live View")

        dw.integrate_buffer_to_np()

        self.pause_start_time = time.time()


    def resume_recording(self):

        dw = self.datawindow

        if self.pause_start_time is not None:
            pause_duration = time.time() - self.pause_start_time
            self.total_pause_time += pause_duration
            self.pause_start_time = None  # reset

        dw.live_mode = True 
        self.pause_live_button.setEnabled(True)
        self.pause_live_button.setToolTip("Pause Live View")


        self.datawindow.plot_update_timer.start()



    def stop_recording(self):
        self.datawindow.plot_update_timer.stop()
        self.datawindow.buffer_data.clear()

        self.datawindow.live_mode = False
        self.pause_live_button.setEnabled(False)
        self.pause_live_button.setToolTip("Connect to Engineering UI to enable live mode")
        self.add_comment_button.setEnabled(False)
        self.add_comment_button.setToolTip("Connect to Engineering UI to enable commenting")



