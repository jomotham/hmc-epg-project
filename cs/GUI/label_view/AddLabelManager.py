from pyqtgraph import InfiniteLine, LinearRegionItem, mkBrush, mkPen
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QDialogButtonBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from utils.TextEdit import TextEdit
from label_view.LabelArea import LabelArea


class AddLabelManager:
    def __init__(self, datawindow):
        self.dw = datawindow
        self.active = False
        self.first_time = None
        self.second_click_pending = False
        self.dragging = False

        self.line1 = InfiniteLine(angle=90, movable=False, pen='b')
        self.line2 = InfiniteLine(angle=90, movable=False, pen='b')
        self.region = LinearRegionItem(
            orientation='vertical', 
            pen=mkPen(QColor(80, 130, 255), width=4),
            brush=mkBrush(QColor(0, 0, 255, 50)), 
            movable=False
        )

        self.fade_overlay = LinearRegionItem(
            orientation='vertical',
            movable=False,
            brush=mkBrush(QColor(255, 255, 255, 120)),  # semi-transparent white
            pen=None  # No border
        )

        for item in [self.line1, self.line2, self.region]:
            item.setZValue(20)
            item.setVisible(False)
            self.dw.plot_item.addItem(item)

        self.fade_overlay.setZValue(5)
        self.fade_overlay.setVisible(False)
        self.dw.plot_item.addItem(self.fade_overlay)

    def start(self):
        self.active = True
        self.first_time = None
        self.dragging = False
        self.dw.selection.deselect_all()

        # Span the full data range on x-axis
        if self.dw.file in self.dw.epgdata.dfs:
            df = self.dw.epgdata.dfs[self.dw.file]
            if not df.empty:
                x_min = df['time'].iloc[0]
                x_max = df['time'].iloc[-1]
                self.fade_overlay.setRegion((x_min, x_max))
                self.fade_overlay.setVisible(True)

    def cancel(self):
        self.active = False
        self.first_time = None
        self.dragging = False
        self.second_click_pending = False
        for item in [self.line1, self.line2, self.region, self.fade_overlay]:
            item.setVisible(False)

    def toggle(self):
        if self.active:
            self.cancel()
        else:
            self.start()

    def mouse_press(self, x: float):
        if not self.active:
            return

        if self.first_time is None:
            # First click
            self.first_time = x
            self.second_click_pending = True  # enable second-click finalization

            for item in [self.line1, self.line2, self.region]:
                item.setVisible(True)
            self.line1.setValue(x)
            self.line2.setValue(x)
            self.region.setRegion((x, x))

        elif self.second_click_pending:
            # Second click finalizes
            self.finalize_label(x)

    def mouse_release(self, x: float):
        if self.active and self.first_time is not None and self.dragging:
            self.finalize_label(x)

    def mouse_move(self, x: float):
        if self.active and self.first_time is not None:
            self.dragging = True  # enable drag mode if movement happens
            self.line2.setValue(x)
            self.region.setRegion((min(self.first_time, x), max(self.first_time, x)))

    def finalize_label(self, second_time: float):
        # Prompt for label
        dialog = QDialog(self.dw)
        dialog.setWindowTitle("Waveform Label")
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Enter Waveform Label:"))

        input_field = TextEdit()
        input_field.setFixedSize(50,25)
        input_field.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        input_field.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        input_field.setStyleSheet("""
            QTextEdit:focus {
                border-bottom: 1px solid #4aa8ff;
            }
        """)
        
        layout.addWidget(input_field)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(buttons)

        input_field.returnPressed.connect(dialog.accept)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        dialog.setLayout(layout)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            self.cancel()
            return

        label = input_field.toPlainText().strip().upper()
        if not label:
            self.cancel()
            return
        
        for item in [self.line1, self.line2, self.region]:
            item.setVisible(False)

        self.second_click_pending = False
        start, end = sorted([self.first_time, second_time])
        duration = end - start

        # Build updated label list
        new_labels = []
        inserted = False

        for la in self.dw.labels:
            s0 = la.start_time
            e0 = s0 + la.duration

            if start <= s0 and e0 <= end:
                # Existing label fully contained - remove it
                for item in la.getItems():
                    if item.scene() is not None:
                        item.scene().removeItem(item)
                continue

            elif s0 < start < e0 and s0 < end < e0:
                # New label fully contained within an existing label - split it two
                left_dur = start - s0
                right_dur = e0 - end

                # Truncate original
                la.duration = left_dur
                la.set_transition_line('right', start)
                la.update_label_area()
                new_labels.append(la)

                # Add new label (middle)
                new_label = LabelArea(start, duration, label, self.dw)
                new_labels.append(new_label)

                # Add copied right half
                new_right = LabelArea(end, right_dur, la.label, self.dw)
                new_right.set_transition_line('left', end)
                new_labels.append(new_right)

                inserted = True
                continue

            elif s0 < start < e0:
                la.duration = start - s0
                la.set_transition_line('right', start)
                la.update_label_area()

            elif s0 < end < e0:
                la.start_time = end
                la.duration = e0 - end
                la.set_transition_line('left', end)
                la.update_label_area()

            new_labels.append(la)

        # Replace label list
        self.dw.labels = new_labels

        if not inserted:
            new_label = LabelArea(start, duration, label, self.dw)

            new_labels.append(new_label)
            new_labels.sort(key=lambda la: la.start_time)
            idx = new_labels.index(new_label)

            new_label.add_right_transition_line()

            self.dw.selection._attempt_snap_and_merge(new_label.right_transition_line)

        new_labels.sort(key=lambda la: la.start_time)
        self.dw.labels = new_labels

        # Merge if needed
        #self.dw.selection.merge_adjacent_labels(new_label)

        # Push to epgdata
        transitions = [(la.start_time, la.label) for la in self.dw.labels]
        self.dw.epgdata.set_transitions(self.dw.file, transitions, self.dw.transition_mode)

        self.dw.update_plot()
        self.cancel()

