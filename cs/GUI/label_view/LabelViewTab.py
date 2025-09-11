
# LabelTab.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
    QProgressBar, QScrollBar, QApplication, QSizePolicy,
    QSpacerItem, QToolButton, QMenu
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from label_view.DataWindow import DataWindow
from EPGData import EPGData
from label_view.Labeler import Labeler
from FileSelector import FileSelector



# TODO: fix the cause of the warning
import warnings
warnings.filterwarnings('ignore', module="torch", message="enable_nested_tensor is True.*")

class LabelViewTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.epgdata = self.parent().epgdata
        self.labeler = Labeler(parent=self)

        # file = self.epgdata.current_file
        # self.epgdata.load_data(file)

        self.datawindow = DataWindow(self)
        self.datawindow.viewbox.sigRangeChanged.connect(self.sync_view_to_scroll)

        self.scrollbar = QScrollBar(Qt.Orientation.Horizontal)
        self.scrollbar.setMinimum(0)
        self.scrollbar.setMaximum(1000)
        self.scrollbar.setPageStep(100) # value dynamically updated
        self.scrollbar.installEventFilter(self)
        self.scrollbar.sliderMoved.connect(self.sync_scroll_to_view)
        # self.scrollbar.setStyleSheet("""
        #     QScrollBar:horizontal {
        #         background: #ddd;
        #         height: 12px;
        #         margin: 0px;
        #         border-radius: 6px;
        #     }

        #     QScrollBar::handle:horizontal {
        #         background: #666;
        #         border-width: 1px;
        #         border: 1px solid #000;
        #         border-radius: 6px;
        #         min-width: 40px;
        #     }

        #     QScrollBar::handle:horizontal:hover {
        #         background: #444;
        #     }

        #     QScrollBar::add-line:horizontal,
        #     QScrollBar::sub-line:horizontal {
        #         background: none;
        #         width: 0px;
        #     }

        #     QScrollBar::add-page:horizontal,
        #     QScrollBar::sub-page:horizontal {
        #         background: none;
        #     }
        # """)


        QApplication.processEvents()
        file = self.parent().epgdata.current_file
        if file is not None:
            self.datawindow.plot_recording(file)

        self.modelChooser = QComboBox()
        self.modelChooser.setMinimumWidth(250)
        self.modelChooser.setEditable(False)

        self.modelChooser.addItem("Select model...")
        self.modelChooser.setItemData(0, 0, Qt.ItemDataRole.UserRole - 1)  # Disable default item

        self.modelChooser.addItem("----- Mosquito Models -----")
        self.modelChooser.setItemData(self.modelChooser.count() - 1, 0, Qt.ItemDataRole.UserRole - 1)

        mosquito_models = ["UNet (Block)", "UNet (Attention)"]
        for model in mosquito_models:
            self.modelChooser.addItem(f"Mosquito {model}")
        
        self.modelChooser.addItem("----- Sharpshooter Models -----")
        self.modelChooser.setItemData(self.modelChooser.count() - 1, 0, Qt.ItemDataRole.UserRole - 1)

        sharpshooter_models = ["UNet (Block)"]
        for model in sharpshooter_models:
            self.modelChooser.addItem(f"Sharpshooter {model}")

        self.modelChooser.currentTextChanged.connect(self.labeler.load_model)

        self.startSplittingButton = QPushButton("Start Probe Splitter")
        self.startSplittingButton.clicked.connect(self.start_splitting)

        self.startSplittingButton.setEnabled(False)
        self.modelChooser.currentTextChanged.connect(self.update_splitting_button_state)

        startLabelingButton = QPushButton("Start Automated Labeling")
        startLabelingButton.clicked.connect(lambda: self.labeler.start_labeling(self.epgdata, self.datawindow))

        # saveDataButton = QPushButton("Save Labeled Data")
        # saveDataButton.clicked.connect(lambda: FileSelector.export_labeled_data(self.epgdata, self.epgdata.current_file))

        # self.progressBar = QProgressBar()
        # self.progressBar.setRange(0, 100)
        # self.progressBar.setMaximumSize(400, 100)
        # #self.progressBar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        # self.progressBar.setStyleSheet("")
        # self.progressBar.setFixedHeight(16)
        # self.labeler.start_labeling_progress.connect(self.update_progress)
        # self.labeler.stopped_labeling.connect(lambda: self.update_progress(0, 100))

        # self.baselineCursorButton = QPushButton("Change to Baseline Cursor")
        # self.baselineCursorButton.clicked.connect(self.switch_cursor_state)

        # A (not great) solution to stopping labeling. Clicking sets a stop flag, the process checks before
        # altering plots (i.e. changing the state) of the GUI. If clicked after, it does nothing. Not superb,
        # but unless we inject some stop signaling way down in the ML code, this is the best as far as I see.
        # stopLabelingButton = QPushButton("Stop Labeling")
        # stopLabelingButton.clicked.connect(self.labeler.stop_labeling)

        settingsButton = QPushButton()
        settingsIcon = QIcon.fromTheme("applications-utilities")
        if settingsIcon.isNull():
            settingsButton.setText("Settings")
        else:
            settingsButton.setIcon(settingsIcon)
        settingsButton.clicked.connect(self.openSettings)

        resetButton = QPushButton("Reset Zoom (R)")
        resetButton.setMinimumWidth(100)
        resetButton.clicked.connect(self.datawindow.reset_view)

        # Top layout
        top_controls = QHBoxLayout()
        #top_controls.addWidget(settingsButton)
        
        top_controls.addStretch(1)
        top_controls.addWidget(resetButton)

        top_controls_widget = QWidget()
        top_controls_widget.setLayout(top_controls)
        top_controls_widget.setStyleSheet("""
            QWidget {
                border-bottom: 1px solid #808080;
            }
        """)

        # Plot Layout
        plot_layout = QVBoxLayout()
        plot_layout.addWidget(self.datawindow)
        plot_layout.addWidget(self.scrollbar)

        # Bottom layout
        bottom_controls = QHBoxLayout()
        #bottom_controls.addWidget(openDataButton)
       
        # bottom_controls.addWidget(self.modelChooser)
        bottom_controls.addWidget(self.modelChooser)
        bottom_controls.addWidget(self.startSplittingButton)
        bottom_controls.addWidget(startLabelingButton)
        # bottom_controls.addWidget(stopLabelingButton)
        # bottom_controls.addWidget(self.progressBar)

        #bottom_controls.addWidget(saveDataButton)

        #bottom_controls_2 = QHBoxLayout()
        #bottom_controls_2.addWidget(self.baselineCursorButton)

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(top_controls_widget)
        main_layout.addLayout(plot_layout) 
        main_layout.addLayout(bottom_controls) 
        #main_layout.addLayout(bottom_controls_2)


        self.setLayout(main_layout)

    def update_splitting_button_state(self, text):
        if "Select model..." in text:
            self.startSplittingButton.setEnabled(False)
        else:
            self.startSplittingButton.setEnabled(True)

    def start_splitting(self):
        selectedModel = self.modelChooser.currentText()
        if "Mosquito" in selectedModel:
            self.labeler.start_mosquito_probe_splitting(self.epgdata, self.datawindow)
        elif "Sharpshooter" in selectedModel:
            self.labeler.start_sharpshooter_probe_splitting(self.epgdata, self.datawindow)
        else:
            print("No model selected.")

    def sync_scroll_to_view(self, slider_value: int):
        if self.datawindow.df is None:
            return

        data_max = self.datawindow.df["time"].iloc[-1]
        (x_min, x_max), _ = self.datawindow.viewbox.viewRange()
        view_width = x_max - x_min

        pan_min = -self.datawindow.viewbox.zoom_viewbox_limit * view_width
        pan_max = data_max - (1 - self.datawindow.viewbox.zoom_viewbox_limit) * view_width
        scroll_span = pan_max - pan_min

        page_step = self.scrollbar.pageStep()
        slider_max = self.scrollbar.maximum()
        effective_range = slider_max - page_step

        x_min = pan_min + (slider_value / effective_range) * (scroll_span - view_width)
        x_min = max(pan_min, min(x_min, pan_max))
        x_max = x_min + view_width

        self.datawindow.viewbox.setXRange(x_min, x_max, padding=0)



    def sync_view_to_scroll(self):
        if self.datawindow.df is None:
            return

        data_max = self.datawindow.df["time"].iloc[-1]
        (x_min, x_max), _ = self.datawindow.viewbox.viewRange()
        view_width = x_max - x_min

        pan_min = -self.datawindow.viewbox.zoom_viewbox_limit * view_width
        pan_max = data_max - (1 - self.datawindow.viewbox.zoom_viewbox_limit) * view_width
        scroll_span = pan_max - pan_min

        slider_max = 1000
        page_step = max(1, int((view_width / scroll_span) * slider_max))
        effective_range = slider_max - page_step


        # Clamp check: ensure slider_value = 0 or max at limits
        if abs(x_min - pan_min) < 1e-6:
            slider_value = 0
        elif abs(x_max - pan_max) < 1e-6:
            slider_value = effective_range
        else:
            slider_value = int(((x_min - pan_min) / (scroll_span - view_width)) * effective_range)

        self.scrollbar.blockSignals(True)
        self.scrollbar.setMaximum(slider_max)
        self.scrollbar.setPageStep(page_step)
        self.scrollbar.setValue(slider_value)
        self.scrollbar.blockSignals(False)



    def update_progress(self, current, total):
        self.progressBar.setValue(int((current / total) * 100))

    def switch_cursor_state(self):
        self.datawindow.cursor_state = not self.datawindow.cursor_state
        self.baselineCursorButton.setText(
            "Change to Normal Cursor" if self.datawindow.cursor_state else "Change to Baseline Cursor"
        )

    def openSettings(self):
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def eventFilter(self, obj, event):
        if obj == self.scrollbar and event.type() == event.Type.Wheel:
            return True  # block the wheel event
        return super().eventFilter(obj, event)


