from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QMainWindow

from ui_python.epg_control_ui import Ui_EPGControl
from PyQt6.QtWidgets import QMainWindow, QSlider, QComboBox, QHBoxLayout, QPushButton
from PyQt6.QtSerialPort import QSerialPort, QSerialPortInfo
from PyQt6.QtCore import Qt, qDebug, QIODevice, pyqtSignal, QTimer, QMetaObject, Q_ARG, pyqtSlot

from cs_code.EPGSocket import SocketClient
from cs_code.ConnectionIndicator import ConnectionIndicator

from queue import Empty
import json
import threading


PGA2_GAIN_MAP = {
    1.0: int(1),
    2.0: int(2),
    3.0: int(5),
    4.0: int(10),
    5.0: int(20),
    6.0: int(50),
    7.0: int(100),
}

class EPGControl(QMainWindow, Ui_EPGControl):
    update = pyqtSignal(str)
    valueChanged = pyqtSignal(str, float)  # signal name, new value
    state_sync_ready = pyqtSignal()

    def __init__(self, parent=None):
        """GUI for controlling values of the EPG. Changing values and applying
        them should cause the EPG to register these changes
        """
        super().__init__(parent)
        self.setupUi(self)


        self.socket_client = SocketClient(client_id="ENGR", parent=self)
        self.socket_client.connectionChanged.connect(self._on_connection_changed)
        self.receive_thread = None  # the thread holding the message receive loop

        self.state_sync_ready.connect(self.send_full_control_state)

        self._suppress_control_signal: bool = False  # prevents circular feedback loop

        self.setupUi(self) 

        self.defaultValues = [1000.0, 0.0, 0.0, 0.0, 0.0]
        self.channel = 1
        #print(f"EPGControl instance ID: {id(self)}")  # Debugging

        # Group sliders and text inputs into lists for easier management
        self.sliders = [
            self.pga1Slider,
            self.ddsoSlider,
            self.ddsaSlider,
            self.pga2Slider,
            self.scaSlider,
            self.scoSlider,
            self.d0Slider,
            self.d1Slider,
            self.d2Slider,
            self.d3Slider,
        ]
        self.textInputs = [
            self.pga1Input,
            self.ddsoInput,
            self.ddsaInput,
            self.pga2Input,
            self.scaInput,
            self.scoInput,
            self.d0Input,
            self.d1Input,
            self.d2Input,
            self.d3Input,
        ]
        self.menuInputs = [self.inputResistanceInput, self.excitationFrequencyInput]

        self.ChangedVals = False

        self.defaultValues = {
            "pga1": 1,
            "pga2": 1,
            "sca": 2,
            "sco": 6,
            "ddso": -34,
            "ddsa": -100,
            "d0": 254,
            "d1": 127,
            "d2": 127,
            "d3": 127
        }

        self.pga1Slider.setMinimum(1)
        self.pga2Slider.setMinimum(1)
        self.scaSlider.setMinimum(2)
        self.scaSlider.setMaximum(7000)
        self.ddsoSlider.setMaximum(100)
        self.ddsoSlider.setMinimum(-100)
        self.d0Slider.setMinimum(0)
        self.d0Slider.setMaximum(254)
        self.d1Slider.setMinimum(1)
        self.d1Slider.setMaximum(127)
        self.d2Slider.setMinimum(0)
        self.d2Slider.setMaximum(255)
        self.d3Slider.setMinimum(0)
        self.d3Slider.setMaximum(255)

        self.updateCurrentValues(typeVal="All")
        # Connect values of the sliders and the text inputs together so that
        # if one changes, the other does too
        for i in range(len(self.sliders)):
            self.sliders[i].valueChanged.connect(
                self.connectHelper(i, self.sliderValueChanged)
            )
            self.textInputs[i].textEdited.connect(
                self.connectHelper(i, self.inputValueChanged)
            )

        self.inputResistanceInput.currentIndexChanged.connect(lambda: self.updateCurrentValues("0"))
        self.inputResistanceInput.currentIndexChanged.connect(
            lambda: self.send_control_update("inputResistance", self.inputResistanceInput.currentText())
        )
        self.excitationFrequencyInput.currentIndexChanged.connect(lambda: self.updateCurrentValues("1"))
        self.excitationFrequencyInput.currentIndexChanged.connect(
            lambda: self.send_control_update("excitationFrequency", self.excitationFrequencyInput.currentText())
        )

        
        # NOTE (CS): UI code placed here for now since the actual UI-defining file is auto-generated
        # from somewhere else
        self.verticalLayout.addStretch()

        self.connectionLayout = QHBoxLayout()

        self.connectionIndicator = ConnectionIndicator()      
        self.connectionIndicator.setObjectName(u"connectionIndicator")
        self.connectionLayout.addWidget(self.connectionIndicator)

        self.connectCSBtn = QPushButton("Connect to CS Socket")
        self.connectCSBtn.setObjectName(u"connectCSBtn")
        self.connectionLayout.addWidget(self.connectCSBtn)

        self.verticalLayout.addLayout(self.connectionLayout)


        # Setup connections for button actions
        self.onBtn.clicked.connect(self.onEPG)
        self.startBtn.clicked.connect(self.startEPG)
        self.offBtn.clicked.connect(self.offEPG)
        self.revertToDefaultsBtn.clicked.connect(self.revertToDefaults)

        self.currentValues = {
            "pga1": self.pga1Slider.value(),
            "pga2": self.pga2Slider.value(),
            "sca": self.scaSlider.value(),
            "sco": self.scoSlider.value(),
            "ddsa": self.ddsaSlider.value(),
            "ddso": self.ddsoSlider.value(),
            "d0": self.d0Slider.value(),
            "d1": self.d1Slider.value(),
            "d2": self.d2Slider.value(),
            "d3": self.d3Slider.value(),
        }

        self._suppress = set()
        
        # Whenever a slider value is changed, a signal is emitted to handleDependencies to change the other sliders it corresponds to
        self.valueChanged.connect(self.handleDependencies)

        # Initialize
        self.revertToDefaults()

        self.connectCSBtn.clicked.connect(self.toggleCSConnection)

        # Store all non-button controls
        self.controls = {
            "inputResistance": self.inputResistanceInput,
            "pga1": self.pga1Slider,
            "pga2": self.pga2Slider,
            "sca": self.scaSlider,
            "sco": self.scoSlider,
            "ddso": self.ddsoSlider,
            "ddsa": self.ddsaSlider,
            "d0": self.d0Slider,
            "d1": self.d1Slider,
            "d2": self.d2Slider,
            "d3": self.d3Slider,
            "excitationFrequency": self.excitationFrequencyInput,
        }
        for key, control in self.controls.items():
            if isinstance(control, QSlider):
                control.valueChanged.connect(lambda val, name=key: self.send_control_update(name, val))

        # map button names to corresponding functions
        self.button_map = {
            "on": self.onEPG,
            "start": self.startEPG,
            "off": self.offEPG,
            "revert": self.revertToDefaults,
        }

    def updateCurrentValues(self, typeVal):
        """Update the current values based on user interaction or initialization."""
        self.ChangedVals = True
        self.ri = self.riReader(self.menuInputs[0].currentText())
        self.freq = int(self.menuInputs[1].currentText())
        self.pga1 = self.sliders[0].value()
        self.ddso = self.sliders[1].value() * 0.1
        self.ddsa = self.sliders[2].value() * 0.01
        self.pga2 = self.sliders[3].value()
        self.sca = self.sliders[4].value()
        self.sco = self.sliders[5].value() * 0.1
        self.d0 = self.sliders[6].value()
        self.d1 = self.sliders[7].value()
        self.d2 = self.sliders[8].value()
        self.d3 = self.sliders[9].value()
        self.on = 0
        self.start = 0
        self.off = 0
        self.typeVal = typeVal

    def connectHelper(self, i: int, func):
        """Helper function needed due to Python's lazy eval which prevents
        functions from being passed into QT's connect functions properly
        :param i: the index that represents which sliders/input changed
        :param func: the function to apply given some signal
        :return: the function that should be connected to the signal
        """
        return lambda event: func(event, i)

    def sliderValueChanged(self, event: int, i: int):
        """If slider is changed, then update the value of the input box
        :param event: the value the slider has been set to
        :param i: the index representing which slider has been changed
        """
        self.textInputs[i].setText(str(event))
        # TODO Put in the scale here
        key = self.sliders[i].objectName().replace("Slider", "").lower()
        self.currentValues[key] = event
        print(f"Emitting valueChanged for {key} with {event}")
        self.valueChanged.emit(key, event)
        self.updateCurrentValues(typeVal= f"{i+3}")

    def inputValueChanged(self, event: str, i: int):
        """If input is changed, then update the value of the slider
        :param event: the value the input has been set to
        :param i: the index representing which input has been changed
        """
        if event == "":
            # Don't update slider or currentValues yet — wait for valid input
            return
        
        try:
            val = int(float(event))
        except ValueError:
            # If input is invalid (like just "-"), do nothing
            return
        
            # TODO Put in the scale here
        val = int(float(event))
        self.sliders[i].setValue(val)
        key = self.textInputs[i].objectName().replace("Input", "").lower()
        self.currentValues[key] = val
        self.valueChanged.emit(key, val)
        self.updateCurrentValues(typeVal=f"{i+3}")

    def revertToDefaults(self):
        """Set all sliders to the default"""
        self.pga1Slider.setValue(self.defaultValues["pga1"])
        self.pga2Slider.setValue(self.defaultValues["pga2"])
        self.scaSlider.setValue(self.defaultValues["sca"])
        self.scoSlider.setValue(self.defaultValues["sco"])
        self.ddsoSlider.setValue(self.defaultValues["ddso"])
        self.ddsaSlider.setValue(self.defaultValues["ddsa"])
        self.d1Slider.setValue(self.defaultValues["d1"])

    def handleDependencies(self, changedKey: str, value: float):
        
        self.currentValues[changedKey] = value

        if changedKey in ["pga1", "pga2", "d1"]:
            if "pga1" in self.currentValues and "pga2" in self.currentValues and "d1" in self.currentValues:
                print(f"handleDependencies called with {changedKey} = {value}")
                new_sca = int(self.currentValues["pga1"] * PGA2_GAIN_MAP.get(self.currentValues["pga2"]) * 254/self.currentValues["d1"])
                if new_sca < 2:
                    new_sca = 2
                elif new_sca > 7000:
                    new_sca = 7000
                self.setControlValue("sca", new_sca, exclude=["pga1", "pga2", "d1"])
             #   wiper_position = (DIGIPOT_MAX_STEPS - 1) / desired_opamp_gain

        if changedKey == "sca":
            print(f"handleDependencies called with {changedKey} = {value}")
            self.set_signal_chain_amplification(value)
            return
        
        if changedKey == "sco":
            # wiper_position = ((((desired_offset / 3.3) + 1) / 2) * 255)
            new_d2 = int(((int(self.currentValues["sco"])/10/3.3 + 1) / 2) * 255)
            self.setControlValue("d2", new_d2, exclude=["sco"])

        if changedKey == "d2":
            # desired_offset = (((wiper_position / 255) * 2) - 1) * 3.3
            new_sco = int(10*((int(self.currentValues["d2"])/255 * 2) - 1) * 3.3)
            self.setControlValue("sco", new_sco, exclude=["d2"])

        if changedKey == "ddso":
            # wiper_position = ((((desired_offset / 3.3) + 1) / 2) * 255)
            new_d3 = int(((int(self.currentValues["ddso"])/100/3.3 + 1) / 2) * 255)
            self.setControlValue("d3", new_d3, exclude=["ddso"])

        if changedKey == "d3":
            # desired_offset = (((wiper_position / 255) * 2) - 1) * 3.3
            new_ddso = int(100*((int(self.currentValues["d3"])/255 * 2) - 1) * 3.3)
            self.setControlValue("ddso", new_ddso, exclude=["d3"])

        if changedKey == "ddsa":
            # wiper_position = (51 * (desired_amplification + 5)) for 10 K resistor
            new_d0 = int(51 * (int(self.currentValues["ddsa"])/100 + 5))
            self.setControlValue("d0", new_d0, exclude=["ddsa"])

        if changedKey == "d0":
            # desired_amplification = (wiper_position / 51) - 5 for 10 K resistor
            new_ddsa = int(100*((int(self.currentValues["d0"]) / 51) - 5))
            self.setControlValue("ddsa", new_ddsa, exclude=["d0"])
    
    def setControlValue(self, key, val, exclude=[]):
        if key in exclude or key in self._suppress:
            return

        old_suppress = self._suppress.copy() # save a copy of previous suppression
        self._suppress.update(exclude) # suppress everything in exclude

        self.currentValues[key] = val
        

        slider = getattr(self, key + "Slider", None)
        inputBox = getattr(self, key + "Input", None)

        if slider:
            slider.blockSignals(True)
            print(f"Setting {key}Slider to {int(val)}")
            slider.setValue(int(val))
            slider.blockSignals(False)

        if inputBox:
            inputBox.blockSignals(True)
            inputBox.setText(str(round(val, 3)))
            inputBox.blockSignals(False)

        self.valueChanged.emit(key, val)  # propagate if not in exclude
        
        # Restore previous suppression state, getting rid of new suppressions
        self._suppress = old_suppress
    #
    #
    def set_signal_chain_amplification(self, desired_amplification):
        MIN_AMPLIFICATION = 2.0
        MAX_AMPLIFICATION = 7000.0

        if desired_amplification < MIN_AMPLIFICATION or desired_amplification > MAX_AMPLIFICATION:
            print("Error: Desired amplification must be between 2x and 7000x")
            return

        remaining_gain = desired_amplification / 2.0  # Head amp stability constraint

        # ---- PGA1: 1x–7x ----
        if remaining_gain >= 7.0:
            pga1_gain = 7
        elif remaining_gain >= 6.0:
            pga1_gain = 6
        elif remaining_gain >= 5.0:
            pga1_gain = 5
        elif remaining_gain >= 4.0:
            pga1_gain = 4
        elif remaining_gain >= 3.0:
            pga1_gain = 3
        elif remaining_gain >= 2.0:
            pga1_gain = 2
        else:
            pga1_gain = 1
        pga1_setting = pga1_gain  # pga1 gain is the same as its setting
        remaining_gain /= pga1_gain

        # ---- PGA2: 1x–100x ----
        if remaining_gain >= 100.0:
            pga2_gain = 100
            pga2_setting = 7
        elif remaining_gain >= 50.0:
            pga2_gain = 50
            pga2_setting = 6
        elif remaining_gain >= 20.0:
            pga2_gain = 20
            pga2_setting = 5
        elif remaining_gain >= 10.0:
            pga2_gain = 10
            pga2_setting = 4
        elif remaining_gain >= 5.0:
            pga2_gain = 5
            pga2_setting = 3
        elif remaining_gain >= 2.0:
            pga2_gain = 2
            pga2_setting = 2
        else:
            pga2_gain = 1
            pga2_setting = 1
        remaining_gain /= pga2_gain
        d1_gain = remaining_gain*2
        # wiper_position = (DIGIPOT_MAX_STEPS - 1) / desired_opamp_gain
        d1_setting = int(254/d1_gain)

        # ---- Update UI sliders/inputs safely ----
        self.setControlValue("pga1", pga1_setting, exclude=["sca", "pga2", "d1"])
        self.setControlValue("pga2", pga2_setting, exclude=["sca", "pga1", "d1"])
        self.setControlValue("d1", d1_setting, exclude=["sca", "pga1", "pga2"])

    def getVals(self):
        UpdatedVals = [self.ri, self.freq, self.pga1, self.ddso, self.ddsa, self.pga2, self.sca, self.sco, self.d0, self.d1, self.d2, self.d3, self.on, self.start, self.off]
        return UpdatedVals, self.typeVal 

    def onEPG(self):
        """Turn system on"""
        self.ChangedVals = True
        self.on = 1
        self.typeVal = "13"
        print(self.typeVal)

    def startEPG(self):
        """Start recording ADC data"""
        self.ChangedVals = True
        self.start = 1
        self.typeVal = "15"
        print(self.typeVal)
    
    def offEPG(self):
        """Turn system off"""
        self.ChangedVals = True
        self.off = 1
        self.typeVal = "14"
        print(self.typeVal)

    def riReader(self, text: str):
        """Conversion for input resistance"""
        if text == "":
            return 
        elif text == "1G Loopback":
            return 0
        elif text == "SR":
            return 5
        suffix = text[-1]
        match suffix:
            case "K":
                return int(text[:-1]) * 10**3
            case "M":
                return int(text[:-1]) * 10**6
            case "G":
                return int(text[:-1]) * 10**9
            

    # ======== Socket Implementation ========    

    def _on_connection_changed(self, is_connected: bool) -> None:
        """
        Slot triggered when this client's connection status changes.

        Updates the connection button text and connection indicator based on the
        new connection status.

        Parameters:
            is_connected (bool): True if connected to the CS socket, False otherwise.
        """
        if is_connected:
            self.connectCSBtn.setText("Disconnect from CS")
            self.connectionIndicator.set_connected(True)
        else:
            self.connectCSBtn.setText("Connect to CS")
            self.connectionIndicator.set_connected(False)

    def toggleCSConnection(self) -> None:
        """
        Toggles the socket connection to the CS client.

        If already connected, disconnects the socket and stops the receive thread.
        If not connected, initiates a new connection and starts the background
        receive thread to handle incoming messages.
        """
        if self.socket_client.connected:
            self.socket_client.disconnect()
            self.receive_thread = None
            print("Disconnected from CS socket")
        else:
            self.socket_client.connect()
            if self.receive_thread is None or not self.receive_thread.is_alive():
                self.receive_thread = threading.Thread(target=self._socket_recv_loop, daemon=True)
                self.receive_thread.start()
                if self.receive_thread.is_alive():
                    print("Connected to CS socket")


    def send_control_update(self, name: str, value):
        """
        Sends a control update message over the socket.

        This is used to transmit a change in an individual control (e.g., slider or
        combo box) to the CS client. If control updates are being suppressed
        (e.g., due to programmatic UI updates), this does nothing.

        Parameters:
            name (str): The name/ID of the control being updated.
            value (Any): The new value of the control.
        """
        if not self.socket_client.connected:
            return
        
        if self._suppress_control_signal:
            return
        
        msg = {
            "source": self.socket_client.client_id,
            "type": "control", 
            "name": name, 
            "value": value
        }

        self.socket_client.send(msg)

    def send_full_control_state(self) -> None:
        """
        Sends the complete current state of all controls to the CS client.

        This includes the values of combo box selections and sliders. It is typically
        used during initial connection to synchronize control state.
        """
        if not self.socket_client.connected:
            return
    
        full_state = {}

        # Add menu inputs (QComboBox)
        full_state["inputResistance"] = self.inputResistanceInput.currentText()
        full_state["excitationFrequency"] = self.excitationFrequencyInput.currentText()
        # Add sliders (hardcoded)
        slider_names = [
            "ddso", "ddsa", "sca", "sco",
        ]
        
        for name, slider in zip(slider_names, self.sliders):
            full_state[name] = slider.value()

        # Send to server
        msg = {
            "source": self.socket_client.client_id,
            "type": "state_sync",
            "value": full_state
        }
        self.socket_client.send(msg)

    @pyqtSlot(str, object, str)
    def set_control_value(self, name, value, source = None) -> None:
        """
        Updates the value of a control in the UI, typically in response to a
        control message received over the socket.

        Ensures that slider and combo box values are only changed if needed,
        and suppresses signal propagation during the update to prevent feedback loops.

        Parameters:
            name (str): Name of the control to update.
            value (Any): New value to set for the control.
            source (str, optional): The sender of the message, used to prevent
                                    reflecting changes back to the sender.
        """
        if source == self.socket_client.client_id:
            return
        
        print(f"[SOCKET] CS: {name} = {value}")
        
        widget = self.controls.get(name)
        if widget is None:
            print(f"[ENGR] Unknown control name: {name}")
            return
        
        self._suppress_control_signal = True
    
        if isinstance(widget, QSlider):
            value = int(value)
            if widget.value() != value:
                widget.setValue(value)
        if isinstance(widget, QComboBox):
            index = widget.findText(str(value))
            if index != -1 and widget.currentIndex() != index:
                widget.setCurrentIndex(index)

        QTimer.singleShot(0, lambda: setattr(self, "_suppress_control_signal", False))


    def _socket_recv_loop(self) -> None:
        """
        Background thread function that receives and handles incoming socket messages.

        Handles:
        - Initial server acknowledgment (`ack`) and emits `state_sync_ready`.
        - Incoming control updates (sliders, combo boxes, buttons).
        - JSON message decoding and command routing.

        Runs until the socket is disconnected.
        """
        acknowledged = False  # whether the client has been acknowledged by the server
        while True:
            if not self.socket_client.connected:
                break
            try:
                # NOTE: message can include multiple commands/data, i.e. "{<command1>}\n{<command2>}\n"
                raw_message = self.socket_client.recv_queue.get(timeout=1.0)

                if not acknowledged:
                    if raw_message.strip() == "ack":
                        acknowledged = True
                        self.state_sync_ready.emit()
                    continue

                # parse message into individual commands
                if isinstance(raw_message, dict):
                    messages = [raw_message]
                else:
                    message_list = raw_message.strip().split("\n")
                    messages = [json.loads(s) for s in message_list if s.strip()]

                for message in messages:
                    if message["source"] == self.socket_client.client_id:
                        continue

                    message_type = message['type']

                    if message_type == "control":
                        name = message["name"]
                        value = message["value"]
                        source = message.get("source")

                        if value == "clicked":  # from a QPushButton
                            func = self.button_map.get(name)
                            if func:
                                func()  # call the corresponding function
                            continue

                        # Workaround to get set_control_value to run in the GUI thread
                        # Might be cleaner to use signals, but this works for now
                        QMetaObject.invokeMethod(
                            self,
                            "set_control_value",
                            Qt.ConnectionType.QueuedConnection,
                            Q_ARG(str, name),
                            Q_ARG(object, value),
                            Q_ARG(str, source)
                        )

            except Empty:
                continue
            except Exception as e:
                print("[SOCKET RECEIVE ERROR]", e)
                continue
                


        