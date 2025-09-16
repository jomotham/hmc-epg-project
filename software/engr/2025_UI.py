"""
This code contains the EPG controls for communicating with the nrf5340 dk
over Bluetooth as well as the graphing software for plotting the data received
from the ADC.
"""
# Code was adapted from this guy’s Github repo: https://github.com/iskandarputra/Real-Time-Py-Serial-Plotter/tree/main

import sys
import numpy as np
from PyQt6.QtCore import Qt, QCoreApplication, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QVBoxLayout,
    QWidget,
    QPushButton,
    QFileDialog,
    QComboBox,
    QLineEdit,
    QTextEdit,
    QMessageBox,
    QSlider,
    QSplitter,
    QWidget,
    QDockWidget,
    QStatusBar,
    QInputDialog)
from PyQt6.QtGui import (
    QAction
)

from PyQt6.QtSerialPort import QSerialPort
import pyqtgraph as pg
import csv
import time  # Import time module for optional delay

# Import last year's EPGControl class for easier management of sliders and buttons
from epg_control2 import EPGControl

# Import libraries needed for Bluetooth
from bleak import BleakClient
import asyncio
import bleak.backends.winrt.util as wutil

import threading
import struct

import json
import os

import soundfile as sf
from collections import deque
import sounddevice as sd



CHARACTERISTIC_UUID = "445817D2-9E86-1078-1F76-703DC002EF42"
WRITE_CHARACTERISTIC_UUID = "445817D2-9E86-1078-1F76-703DC002EF43"
# Use one of the following addresses depending on which digi board using
address = "C2:83:79:F8:C2:86" # CS's board

class CircularBuffer:
    def __init__(self, capacity):
        self.capacity = capacity
        self.buffer = np.zeros(capacity)
        self.index = 0
        self.full = False

    def push(self, value):
        self.buffer[self.index] = value
        self.index = (self.index + 1) % self.capacity
        if self.index == 0:
            self.full = True

    def get_data(self):
        if self.full:
            return np.concatenate((self.buffer[self.index:], self.buffer[:self.index]))
        else:
            return self.buffer[:self.index]


class SerialPlotterWindow(QMainWindow):
    ble_data_received = pyqtSignal(str)  # send the raw string line

    def __init__(self):
        super().__init__()

        # self.setWindowTitle("Real-Time Py Serial Viewer")
        self.setWindowTitle("Real-Time EPG Visualizer")
        self.setGeometry(500, 500, 800, 600)

        # For Bluetooth
        self.ble_connected = False
        self.ble_chosen = False

        # Create dual view EPG control + graph
        self.setupMainLayout()

        # Create Actions that will be linked to user interactions
        self._createActions()

        # Populate menu items (File, View, Target, etc.)
        self._createMenu()

        self._createConnectivityStatusBar()

        self.ble_data_received.connect(self.receive_ble_data)

        #self.epgControl = EPGControl()

        self.serial_port = QSerialPort()
        self.serial_port.setPortName(
            "/dev/tty.usbmodem0010500967183")  # Adjust for your system
        self.serial_port.setBaudRate(115200)  # used to be 115200

        self.is_paused = False
        self.data_records = []

        """Connect to Device"""
        self.address_history_path = "ble_addresses.json"
        self.ble_address_history = self.load_ble_address_history()

        """Echo Port Settings"""
        self.audio_sample_rate = 384000  # DAC sample rate
        self.input_sample_rate = 40   # Bluetooth ADC rate. It's 50 to accomoate for dropped samples.
        self.output_buffer = deque()
        
        # wav file saving settings
        self.wav_file_path = f"live_stream.wav"

        self.wav_stream = sf.SoundFile(
            self.wav_file_path, mode='w', samplerate=self.audio_sample_rate,
            channels=1, subtype='PCM_32'
        )
        
        # audio streaming settings
        self.audio_stream = None
        self.stream_blocksize = int(self.audio_sample_rate / self.input_sample_rate)  

    def _createMenu(self):
        """
        Create menu bar with various actions for file operations and settings.
        Connect actions with respective menu items
        """

        targetMenu = self.menuBar().addMenu("&Device Connection")
        targetMenu.addAction(self.ConnectToDevice) 
        targetMenu.addAction(self.disconnectFromDevice)
        

    def _createActions(self):
        # Open EPG control window
        self.epgControlAction = QAction("&Open EPG Control", self)
        self.epgControlAction.triggered.connect(self.showEpgControl)

          # Connect to Bluetooth
        self.ConnectToDevice = QAction("&Connect Bluetooth", self)
        self.ConnectToDevice.triggered.connect(self.connect_dialog)

        # Disconenct to device (for bluetooth)
        self.disconnectFromDevice = QAction("&Disconnect Bluetooth", self)
        self.disconnectFromDevice.triggered.connect(
            self.disconnectDeviceViaBluetooth)
        
    def createChartView(self):
        self.graph_widget = pg.PlotWidget()
        self.graph_widget.setBackground("#000000")
        self.graph_widget.showGrid(True, True)
        self.graph_widget.setLabel("left", "Values")
        self.graph_widget.setLabel("bottom", "Time")
        self.graph_widget.setMouseEnabled(x=True, y=False)
        self.graph_widget.setClipToView(True)

        self.graph_widget_item = QWidget()
        graph_widget_layout = QVBoxLayout()
        graph_widget_layout.addWidget(self.graph_widget)
        self.graph_widget_item.setLayout(graph_widget_layout)
        self.setCentralWidget(self.graph_widget_item)

        self.sensor_data = {}

        # sampling speeds = [40hz, 500hz, 2000hz, 4000hz]
        self.buffer_sizes = [800, 4000, 10000]
        self.buffer_capacity = self.buffer_sizes[0]

        self.buffer_size_combo = QComboBox()
        self.buffer_size_combo.addItems(
            [str(size) for size in self.buffer_sizes])
        self.buffer_size_combo.setCurrentIndex(0)
        self.buffer_size_combo.currentIndexChanged.connect(
            self.change_buffer_size)

        graph_widget_layout.addWidget(self.buffer_size_combo)

        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(self.on_pause_clicked)
        graph_widget_layout.addWidget(self.pause_button)

        self.resume_button = QPushButton("Resume")
        self.resume_button.clicked.connect(self.resume_updates)
        graph_widget_layout.addWidget(self.resume_button)
        self.resume_button.setEnabled(False)

        self.export_button = QPushButton("Export Data")
        self.export_button.clicked.connect(self.export_data)
        graph_widget_layout.addWidget(self.export_button)
        self.export_button.setEnabled(False)
        
        """Echo Port Button"""
        self.echo_port_enabled = False  # Default: Echo Port off
        self.echo_port_button = QPushButton("Enable Echo Port")
        self.echo_port_button.setCheckable(True)
        self.echo_port_button.toggled.connect(self.toggle_echo_port)
        graph_widget_layout.addWidget(self.echo_port_button)
        
        self.save_echo_button = QPushButton("Save Echo Port Output")
        self.save_echo_button.clicked.connect(self.save_echo_output)
        graph_widget_layout.addWidget(self.save_echo_button)




    def setupMainLayout(self):
        """
        Setup a splitter containing EPG controls and the graph and add it to the main layout.
        """

        # Create a splitter to hold both the chart content and the EPG control
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left side - Chart view
        self.createChartView()  # Assuming this creates self.chartView
        splitter.addWidget(self.graph_widget_item)

        # Set the splitter as the central widget of QMainWindow
        self.setCentralWidget(splitter)

        # Create a QDockWidget for EPGControl
        self.epgControlDock = QDockWidget("EPG Control", self)
        self.createEPGControlView()  # Assuming this creates self.epgControlView
        self.epgControlDock.setWidget(self.epgControlView)

        # Enable collapsible and floating behavior for the EPG control
        self.epgControlDock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable |
                                        QDockWidget.DockWidgetFeature.DockWidgetFloatable |
                                        QDockWidget.DockWidgetFeature.DockWidgetClosable)

        # Add the QDockWidget to the right side (it will be collapsible)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.epgControlDock)

        # Set the initial horizontal size of the epgControlDock widget
        self.resizeDocks([self.epgControlDock], [700], Qt.Orientation.Horizontal)

        splitter.addWidget(self.epgControlDock)

    """
   EPG Controller Widget functions
   """

    def createEPGControlView(self):
        """ 
        Create a widget that will be populated with various EPG related
        controls.
        """
        self.epgControlView = EPGControl()
        self.epgControlView.show()
        # print(f"MainWindow control instance ID: {id(self.epgControlView)}")

    def showEpgControl(self):
        self.epgControlView.show()

    def _createConnectivityStatusBar(self):
        # Creating device connectivity status bar in main window.
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.setWindowTitle("Device Status")
        # self.setGeometry(100,100, 100, 200)

        # create a stop event to signal end of thread
        self.stop_ble_event = threading.Event()

        # Timer to periodically check the BLE connection
        self.BLE_timer = QTimer()
        self.BLE_timer.timeout.connect(self.check_ble_connection)
        self.BLE_timer.start(500)  # Check every 0.5 second

        self.check_ble_connection()  # Initial check

        # Allow STA model for asyncio threading
        wutil.allow_sta()

        self.read_ble_thread = threading.Thread(
            target=self.run_async, args=(self.update_ble_status,))
        self.read_ble_thread.daemon = True

    def connectDeviceViaBluetooth(self):
        """Connects to the EPG Device via bluetooth."""
        self.stop_ble_event.clear()
        self.read_ble_thread = threading.Thread(
            target=self.run_async, args=(self.update_ble_status,))
        self.read_ble_thread.daemon = True
        # now set up the ble process
        # Start the BLE service reading in a separate process (so it can run constantly in the background)
        self.read_ble_thread.start()
        self.ble_chosen = True

    def disconnectDeviceViaBluetooth(self):
        """Disconnects from the EPG Device via bluetooth"""
        # Make sure BLE is disconnected
        if self.ble_chosen:
            self.ble_chosen = False
            if self.read_ble_thread.is_alive():  # check to see if thread is still active
                self.stop_ble_event.set()  # set event flag to true
                self.read_ble_thread.join()  # wait for thread to terminate before starting new one
        self.ble_connected = False

    def add_sensor(self, name, color):
        self.sensor_data[name] = {
            'buffer': CircularBuffer(self.buffer_capacity),
            'plot_item': self.graph_widget.plot(pen=pg.mkPen(color, width=2), name=name),
        }

    def change_buffer_size(self, index):
        self.buffer_capacity = self.buffer_sizes[index]
        for sensor in self.sensor_data.values():
            sensor['buffer'] = CircularBuffer(self.buffer_capacity)

    def on_pause_clicked(self):
        self.pause_updates()
        self.export_button.setEnabled(True)

    def pause_updates(self):
        self.is_paused = True
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(True)

    def resume_updates(self):
        self.is_paused = False
        self.pause_button.setEnabled(True)
        self.resume_button.setEnabled(False)
        self.export_button.setEnabled(False)

    def export_data(self):
        if len(self.data_records) > 0:
            filename, _ = QFileDialog.getSaveFileName(
                self, "Export Data", "", "CSV Files (*.csv)")
            if filename:
                try:
                    with open(filename, "w", newline="") as file:
                        writer = csv.writer(file)
                        writer.writerow(["Timestamp", "Value"])
                        writer.writerows(self.data_records)
                    QMessageBox.information(
                        self, "Export Success", "Data exported successfully.")
                except Exception as e:
                    QMessageBox.warning(
                        self, "Export Error", f"Failed to export data: {str(e)}")
            else:
                QMessageBox.warning(self, "Export Error", "Invalid filename.")
        else:
            QMessageBox.warning(self, "Export Error", "No data to export.")

    def receive_ble_data(self, data):
        try:
            # Debug print to see incoming data
            # print(f"Received raw data: {data}")

            # Split the data by the comma (timestamp, voltage)
            values = data.split(",")
            if len(values) == 2:
                try:
                    # Extract timestamp and voltage from the data
                    # Convert timestamp to an integer
                    timestamp = int(values[0].strip())
                    # Convert voltage to a float
                    voltage = (float(values[1].strip()))/1000 # convert to V

                    # FOR CS: send the UNIX timestamp
                    timestamp = time.time()

                    socket_msg = {"type":"data", "value": [timestamp, voltage], "source":"ENGR"}
                    self.epgControlView.socket_client.send(socket_msg)
                    
                    # Normalize for audio output (-0.2V to 3.0V → -1 to 1)
                    norm_voltage = (voltage + 0.2) / (3 + 0.2) * 2 - 1.0
                    norm_voltage = max(min(norm_voltage, 1), -1)
                    # print(f"Raw: {voltage:.3f} V → Normalized: {norm_voltage:.3f}")

                    
                    if self.echo_port_enabled:
                        oversampled = self.oversample_single(norm_voltage)

                        # Play audio stream
                        if len(self.output_buffer) < self.stream_blocksize * 10:  # max ~100ms buffer delay
                            oversampled = self.oversample_single(norm_voltage)
                            self.output_buffer.extend(oversampled)

                            if self.wav_stream and not self.wav_stream.closed:
                                self.wav_stream.write(oversampled)

                        # Write to WAV file
                        if self.wav_stream and not self.wav_stream.closed:
                            self.wav_stream.write(oversampled)
                        
                    else: 
                    # Plotting and export mode
                        if "ADC1" in self.sensor_data and not self.is_paused:
                            data_buffer = self.sensor_data["ADC1"]['buffer']
                            data_buffer.push(voltage)
                            self.sensor_data["ADC1"]['plot_item'].setData(
                                data_buffer.get_data())

                        # Optionally, you can store both timestamp and voltage in your records for export
                        self.data_records.append([timestamp, voltage])

                except ValueError as e:
                    # Handle any parsing errors (e.g., invalid values)
                    print(f"Error parsing data values: {e}")
        except (UnicodeDecodeError, IndexError, ValueError) as e:
            # Log any other parsing issues
            print(f"Error processing data: {e}") 

    def send_command(self):
        """Send a command via UART, one character at a time."""
        command = self.command_input.text().strip()  # Get and clean command input

        if not command:
            return  # Don't send empty commands

        if not self.serial_port.isOpen():
            print("Error: Serial port is not open!")
            return

        try:
            command += "\r"  # Ensure the command ends with '\r'

            for char in command:
                self.serial_port.write(char.encode(
                    'utf-8'))  # Send one character
                self.serial_port.flush()  # Ensure immediate transmission
                # Optional: Small delay to prevent buffer overload
                time.sleep(0.001)

            print(f"Sent command: {command}")  # Debugging print

            # Display the sent command in the QTextEdit widget
            self.sent_commands_display.append(f"Sent: {command}")

            # Clear the input field
            self.command_input.clear()

        except Exception as e:
            print(f"Error sending command: {e}")

    """BLE Device Connection"""

    def load_ble_address_history(self):
        if os.path.exists(self.address_history_path):
            try:
                with open(self.address_history_path, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
            except Exception as e:
                print(f"Failed to load address history: {e}")
        return []


    def save_ble_address_history(self):
        try:
            with open(self.address_history_path, 'w') as f:
                json.dump(self.ble_address_history, f, indent=2)
        except Exception as e:
            print(f"Failed to save address history: {e}")

    def connect_dialog(self):
        dialog = QWidget()
        dialog.setWindowTitle("Bluetooth Connect")
        layout = QVBoxLayout(dialog)

        instructions = QLabel(
            "Enter a new address or select a previously used one:")
        layout.addWidget(instructions)

        self.address_combo = QComboBox()
        self.address_combo.setEditable(True)
        self.address_combo.addItems(self.ble_address_history)
        layout.addWidget(self.address_combo)

        connect_btn = QPushButton("Connect")
        layout.addWidget(connect_btn)

        clear_btn = QPushButton("Clear History")
        layout.addWidget(clear_btn)

        def on_connect_clicked():
            entered_address = self.address_combo.currentText().strip().upper()
            if entered_address:
                if entered_address not in self.ble_address_history:
                    self.ble_address_history.append(entered_address)
                    self.save_ble_address_history()

                self.stop_ble_event.clear()
                self.read_ble_thread = threading.Thread(
                    target=self.run_async_with_address,
                    args=(self.update_ble_status, entered_address)
                )
                self.read_ble_thread.daemon = True
                self.read_ble_thread.start()
                self.ble_chosen = True

                dialog.close()

        def on_clear_history():
            self.ble_address_history = []
            self.address_combo.clear()
            if os.path.exists(self.address_history_path):
                try:
                    os.remove(self.address_history_path)
                except Exception as e:
                    print(f"Failed to delete address history file: {e}")

        connect_btn.clicked.connect(on_connect_clicked)
        clear_btn.clicked.connect(on_clear_history)

        dialog.setLayout(layout)
        dialog.setFixedSize(400, 200)
        dialog.show()


    def check_ble_connection(self):
        """Check if a BLE device is connected."""
        if self.ble_connected:
            self.update_ble_status("Device Status: Connected")
        else:
            self.update_ble_status("Device Status: Disconnected")

    def update_ble_status(self, status_message):
        """Update the status bar message for BLE and UI interactivity."""
        if status_message:
            self.ble_connected = status_message == "Device Status: Connected"
            self.status_bar.showMessage(status_message)

            # Disable connect if already connected
            if hasattr(self, "ConnectToDevice"):
                self.ConnectToDevice.setEnabled(not self.ble_connected)

    """Write updated slider/button values to Bluetooth"""

    async def async_write(self, callback, client):
        if self.epgControlView.ChangedVals:
            Vals, typeVal = self.epgControlView.getVals()   
            # print(Vals)
            await self.write_data(Vals, typeVal, callback, client)
        else:
            pass

    """Main async function to run the read_data_from_nrf"""

    async def main(self, callback):
        await self.read_data_from_nrf(address, callback)
        print("done!")

    """Controls what data gets sent back to Nordic"""

    async def write_data(self, val, typeVal, callback, client):
        try:
            if typeVal == "All":
                val = val[1]
                if val == 1000:
                    data_to_write = bytearray("IDDS", 'utf-8') + b'\0'
                if val == 1:
                    data_to_write = bytearray("SDDS:1", 'utf-8') + b'\0'
                else:
                    data_to_write = bytearray("DDSOFF", 'utf-8') + b'\0'
            elif typeVal == "0":
                val = val[0]
                if val == 100000: # 100K
                    data_to_write = bytearray("M:0", 'utf-8') + b'\0'
                elif val == 1000000: # 1M
                    data_to_write = bytearray("M:1", 'utf-8') + b'\0'
                elif val == 10000000: # 10M
                    data_to_write = bytearray("M:2", 'utf-8') + b'\0'
                elif val == 100000000: # 100M
                    data_to_write = bytearray("M:3", 'utf-8') + b'\0'
                elif val == 1000000000: # 1G
                    data_to_write = bytearray("M:6", 'utf-8') + b'\0'
                elif val == 10000000000: # 10G
                    data_to_write = bytearray("M:4", 'utf-8') + b'\0'
                elif val == 5: # SR
                    data_to_write = bytearray("M:5", 'utf-8') + b'\0'
                elif val == 0: # 1G Loopback
                    data_to_write = bytearray("M:7", 'utf-8') + b'\0'
            elif typeVal == "3":
                val = val[2]
                data_to_write = bytearray("P1:"+str(val), 'utf-8') + b'\0'
            elif typeVal == "4":
                val = val[3]
                data_to_write = bytearray(
                    "DDSO:"+str(round(val, 3)), 'utf-8') + b'\0'
            elif typeVal == "5":
                val = val[4]
                data_to_write = bytearray(
                    "DDSA:"+str(round(val, 3)), 'utf-8') + b'\0'
            elif typeVal == "6":
                val = val[5]
                data_to_write = bytearray("P2:"+str(val), 'utf-8') + b'\0'
            elif typeVal == "7":
                val = val[6]
                data_to_write = bytearray(
                    "SCA:"+str(round(val, 3)), 'utf-8') + b'\0'
            elif typeVal == "8":
                val = val[7]
                data_to_write = bytearray(
                    "SCO:"+str(round(val, 3)), 'utf-8') + b'\0'
            elif typeVal == "9":
                val = val[8]
                data_to_write = bytearray("D0:"+str(val), 'utf-8') + b'\0'
            elif typeVal == "10":
                val = val[9]
                data_to_write = bytearray("D1:"+str(val), 'utf-8') + b'\0'
            elif typeVal == "11":
                val = val[10]
                data_to_write = bytearray("D2:"+str(val), 'utf-8') + b'\0'
            elif typeVal == "12":
                val = val[11]
                data_to_write = bytearray("D3:"+str(val), 'utf-8') + b'\0'
            elif typeVal == "13":
                data_to_write = bytearray("ON", 'utf-8') + b'\0'
            elif typeVal == "14":
                data_to_write = bytearray("OFF", 'utf-8') + b'\0'
            elif typeVal == "15":
                data_to_write = bytearray("START", 'utf-8') + b'\0'
            else:
                val = val[1]
                if val == 1000:
                    data_to_write = bytearray("SDDS:1000", 'utf-8') + b'\0'
                elif val == 1:
                    data_to_write = bytearray("SDDS:1", 'utf-8') + b'\0'
                else:
                    data_to_write = bytearray("DDSOFF", 'utf-8') + b'\0'

            try:
                await client.write_gatt_char(WRITE_CHARACTERISTIC_UUID, data_to_write)
                # print(f"Data {data_to_write} written to characteristic {WRITE_CHARACTERISTIC_UUID}.")
                # Set epgControl.ChangedVals back to False
                self.epgControlView.ChangedVals = False

            except Exception as e:
                print(f"Failed to write/read data: {e}")
                await self.read_data_from_nrf(address, callback)

        except Exception as e:
            print(f"Failed to write/read data: {e}")
            await self.read_data_from_nrf(address, callback)

    """call asyncio.run to start the async processes"""

    def run_async(self, callback):
        while not self.stop_ble_event.is_set():
            try:
                asyncio.run(self.main(callback))
            except Exception as e:
                # print("Wait for connection...")
                callback("Device Status: Disconnected")
                self.run_async(callback)

    def run_async_with_address(self, callback, custom_address):
        while not self.stop_ble_event.is_set():
            try:
                asyncio.run(self.read_data_from_nrf(custom_address, callback))
            except Exception as e:
                callback("Device Status: Disconnected")
                self.run_async_with_address(callback, custom_address)


    """This is the notification handler that gets called 
      whenever Nordic sends over data"""

    def notification_handler(self, sender, data):
        try:
            char_data = data.decode('utf-8')
            self.ble_data_received.emit(char_data)  # send to Qt thread
        except Exception as e:
            print(f"Notification decode error: {e}")
        # print(f"Data from nRF: {(char_data)}")
        # timestamp = char_data.split(",")[0]
        # voltage = char_data.split(",")[1]
        # Plot data
        # self.receive_ble_data(char_data)

    """Function that gets called in BLE thread to start and keep track of  connection"""

    async def read_data_from_nrf(self, address, callback):
        try:
            async with BleakClient(address) as client:
                try:
                    # Start subscribing to notifications
                    await client.start_notify(CHARACTERISTIC_UUID, self.notification_handler)
                    # Continuously poll for data until an error arises
                    while True and not self.stop_ble_event.is_set():
                        # Write back commands to Nordic
                        await self.async_write(callback, client)

                        if client.is_connected:
                            callback("Device Status: Connected")
                            # sample every 0.1 seconds
                            await asyncio.sleep(0.1)
                        else:
                            print("Connection lost, trying to reconnect...")
                            callback("Device Status: Disconnected")
                            await client.connect()
                except Exception as e:
                    print(f"An error occurred: {e}")
                    callback("Device Status: Disconnected")
                    print("Stopping notifications...")
                    await client.stop_notify(CHARACTERISTIC_UUID)
                    await self.main(callback)
        except Exception as e:
            print(f"an error occurred: {e}")
            callback("Device Status: Disconnected")
            await self.main(callback)
            
    """
    ECHO PORT FUNCTIONS
    """

    def oversample_single(self, value):
        # Repeat the value to match audio_sample_rate (e.g. 44100 Hz from 100 Hz input).
        repeat_count = int(self.audio_sample_rate / self.input_sample_rate)
        return np.full(repeat_count, value, dtype=np.float32)
    
    def audio_callback(self, outdata, frames, time, status):
        if len(self.output_buffer) >= frames:
            # Pull enough samples for one block
            chunk = [self.output_buffer.popleft() for _ in range(frames)]
            outdata[:] = np.array(chunk, dtype=np.float32).reshape(-1, 1)
        else:
            # Not enough data — fill with silence (this causes the DAC to glitch)
            print("UNDERRUN!")
            outdata[:] = np.zeros((frames, 1), dtype=np.float32)

    def toggle_echo_port(self, checked):
        self.echo_port_enabled = checked
        if checked:
            self.echo_port_button.setText("Disable Echo Port")
            self.pause_button.setEnabled(False)
            self.resume_button.setEnabled(False)

            # Start audio stream
            if self.audio_stream is None:
                self.audio_stream = sd.OutputStream(
                    samplerate=self.audio_sample_rate,
                    channels=1,
                    dtype='float32',
                    blocksize=self.stream_blocksize,
                    callback=self.audio_callback  # <-- function reference, not a function call
                )
                self.audio_stream.start()

        else:
            self.echo_port_button.setText("Enable Echo Port")
            self.pause_button.setEnabled(True)
            self.resume_button.setEnabled(self.is_paused)

            # Stop audio stream
            if self.audio_stream is not None:
                self.audio_stream.stop()
                self.audio_stream.close()
                self.audio_stream = None

    def closeEvent(self, event):
        # Close the audio stream when the window is closed
        if hasattr(self, 'wav_stream') and not self.wav_stream.closed:
            self.wav_stream.close()
        event.accept()
        if self.audio_stream is not None:
            self.audio_stream.stop()
            self.audio_stream.close()
            
    def save_echo_output(self):
        if hasattr(self, 'wav_stream') and not self.wav_stream.closed:
            self.wav_stream.flush()

        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Echo Port Recording", "", "WAV Files (*.wav)"
        )

        if filename:
            try:
                # Copy the current .wav to the user-specified location
                import shutil
                shutil.copyfile(self.wav_file_path, filename)
                QMessageBox.information(
                    self, "Saved", f"Echo Port output saved to:\n{filename}")
            except Exception as e:
                QMessageBox.warning(
                    self, "Error", f"Failed to save file:\n{str(e)}")
        else:
            QMessageBox.information(self, "Cancelled", "No file selected.")

# Main Program Run
if __name__ == "__main__":
    app = QApplication(sys.argv)

    plotter_window = SerialPlotterWindow()
    plotter_window.add_sensor("ADC1", 'w')

    # if plotter_window.serial_port.open(QSerialPort.ReadWrite):
    # print("Serial port opened successfully.")
    plotter_window.show()
    sys.exit(app.exec())
