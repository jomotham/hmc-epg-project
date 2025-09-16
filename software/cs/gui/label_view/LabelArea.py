from typing import Literal

from pyqtgraph import (
    PlotWidget, ViewBox,
    TextItem, InfiniteLine, LinearRegionItem,
    mkPen, mkBrush,
)
from PyQt6.QtWidgets import QGraphicsRectItem
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QFont, QFontMetricsF, QPen, QColor

from settings import settings

class LabelArea:
    """
    Handles rendering and layout of a labeled region in a waveform plot.
    Used to represent labeled time intervals in waveform recordings.

    Each LabelArea includes:
    - A colored background (`LinearRegionItem`)
    - A transition line (`InfiniteLine`)
    - Label and duration text (`TextItem`)
    - Background rectangles and optional debug boxes
    """
    def __init__(self, time: float, dur: float, label: str, datawindow):
        """
        Initializes a new LabelArea with a label, duration, and graphical elements.

        Parameters:
            time (float): Start time of the label region.
            dur (float): Duration of the labeled region.
            label (str): Label string (e.g. "N", "B2").
            datawindow (DataWindow): The parent DataWnidow managing this label.

        Notes:
            Also connects to the viewbox's transformChanged signal.
        """
        self.datawindow: PlotWidget  # the parent DataWindow
        self.viewbox: ViewBox # the ViewBox object that the LabelArea is being rendered in
        self.text_metrics: QFontMetricsF  # metrics about the font for the text
        self.start_time: float # the time at the start of the label

        self.label: str  # the label string
        self.label_text: TextItem  # the text object holding the label string
        self.label_bbox: QRectF  # the bounding box around the label text
        self.label_background: QGraphicsRectItem  # the background fill for the label text
        self.label_debug_box: QGraphicsRectItem  # the debug bbox for the label

        self.duration: float  # duration of the label in sec
        self.duration_text: TextItem  # the text object holding the duration string
        self.duration_bbox: QRectF  # the bounding box around the duration text
        self.duration_background: QGraphicsRectItem  # the background fill for the dur text
        self.duration_debug_box: QGraphicsRectItem  # the debug bbox for the duration

        self.transition_line: InfiniteLine  # the vertical line starting the LabelArea
        self.right_transition_line: InfiniteLine # optional vertical line if this LabelArea has no right neighbor
        self.area: LinearRegionItem   # the colored FillBetweenItem for the label

        self.enable_debug: bool # whether to show debug boxes
        
        # ----- initialize instance variables --------------------------

        self.datawindow = datawindow
        self.viewbox = self.datawindow.viewbox
        self.start_time = time

        _, (y_min, y_max) = self.viewbox.viewRange()

        centered_x = time + dur / 2
        label_y = y_min + 0.05 * (y_max - y_min)
        duration_y = y_max - 0.05 * (y_max - y_min)

        font = QFont('Sans', 10)
        self.text_metrics = QFontMetricsF(font)

        self.label = label   
        self.label_text = TextItem(label, color=settings.get("plot_theme")["FONT_COLOR_1"], anchor=(0.5, 0.5))
        self.label_text.setFont(font)
        self.label_text.setPos(centered_x, label_y)
        
        self.viewbox.addItem(self.label_text)

        self.duration = dur
        self.duration_text = TextItem(f"{dur:.2f}", color=settings.get("plot_theme")["FONT_COLOR_1"], anchor=(0.5, 0.5))
        self.duration_text.setFont(font)
        self.duration_text.setPos(centered_x, duration_y)
        self.viewbox.addItem(self.duration_text)

        self.enable_debug = self.datawindow.enable_debug

        self.transition_line = InfiniteLine(
            pos=time,
            angle=90,  # vertical
            pen=mkPen(color=settings.get("plot_theme")["TRANSITION_LINE_COLOR"], width=2),
            hoverPen=None,
            movable=False,
        )
        self.viewbox.addItem(self.transition_line)
        self.right_transition_line = None
  
        self.area = LinearRegionItem(
            values = (time, time + dur),
            orientation='vertical',
            brush=mkBrush(color=settings.get_label_color(self.label)),
            hoverBrush=None,
            movable=False,
        )
        self.area.setZValue(-10)
        self.viewbox.addItem(self.area)

        self.label_bbox = self.bounding_box(self.label_text)
        self.duration_bbox = self.bounding_box(self.duration_text)

        self.label_background = self.background_box(self.label_text)
        self.viewbox.addItem(self.label_background)
        
        self.duration_background = self.background_box(self.duration_text)
        self.viewbox.addItem(self.duration_background)

        #QApplication.processEvents()

        self.set_duration_visible(settings.get("show_durations"))

        #self.viewbox.sigTransformChanged.connect(self.update_label_area)   

        if self.enable_debug:
            self.toggle_debug_boxes()   

    def toggle_debug_boxes(self) -> None:
        """
        Adds or removes red debug rectangles around the label and duration text.

        Called when `enable_debug` is toggled or on redraw.
        """
        if self.enable_debug:
            if not hasattr(self, "label_debug_box"):
                self.label_debug_box = QGraphicsRectItem(self.label_bbox)
                self.label_debug_box.setPen(mkPen(color='red'))
            else:   
                self.update_rect(self.label_debug_box, self.label_bbox)
            self.viewbox.addItem(self.label_debug_box)

            if not hasattr(self, "duration_debug_box"):
                self.duration_debug_box = QGraphicsRectItem(self.duration_bbox)
                self.duration_debug_box.setPen(mkPen(color='red'))
            else:
                self.update_rect(self.duration_debug_box, self.duration_bbox)
            self.viewbox.addItem(self.duration_debug_box)    

        else:
            if hasattr(self, "label_debug_box"):
                self.viewbox.removeItem(self.label_debug_box)
            if hasattr(self, "duration_debug_box"):
                self.viewbox.removeItem(self.duration_debug_box)

    def refreshColor(self) -> None:
        self.area.setBrush(mkBrush(color=settings.get_label_color(self.label)))
        self.label_background.setBrush(mkBrush(self.get_background_color()))
        self.duration_background.setBrush(mkBrush(self.get_background_color()))
        self.label_text.setColor(settings.get("plot_theme")["FONT_COLOR_1"])
        self.duration_text.setColor(settings.get("plot_theme")["FONT_COLOR_1"])

        self.transition_line.setPen(mkPen(settings.get("plot_theme")["TRANSITION_LINE_COLOR"], width = 2))
        if self.right_transition_line:
            self.right_transition_line.setPen(mkPen(settings.get("plot_theme")["TRANSITION_LINE_COLOR"], width = 2))


    def setVisible(self, visible: bool) -> None:
        """
        Sets the visibility of all LabelArea components (text, area, background, etc.).

        Parameters:
            visible (bool): Whether to show or hide the label area.
        """
        for item in self.getItems():
            item.setVisible(visible)

    def isVisible(self) -> bool:
        """
        Returns whether the LabelArea is curerntly set to visible or not.
        """
        return self.area.isVisible() # as a proxy for the whole visibility



    def set_duration_visible(self, visible: bool) -> None:
        """
        Sets the visibility of the duration components (text, background).

        Parameters:
            visible (bool): Whether to show or hide the duration.
        """
        self.duration_text.setOpacity(1.0 if visible else 0.0)
        self.duration_background.setOpacity(1.0 if visible else 0.0)
        self.update_label_area()


    def bounding_box(self, text_item: TextItem) -> QRectF:
        """
        Computes the data-space bounding box of a given TextItem.

        Parameters:
            text_item (TextItem): The text to measure.
        Returns:
            QRectF: Bounding box of the text, in ViewBox coordinates.
        """
        # get bounding box from font metrics
        text = text_item.toPlainText()
        raw_rect = self.text_metrics.tightBoundingRect(text)
        raw_rect.adjust(-2,-2, 2, 2) # padding of 2 to match background box visuals

        # get anchor offset
        anchor_x, anchor_y = text_item.anchor
        offset_x = raw_rect.width() * anchor_x
        offset_y = raw_rect.height() * anchor_y

        # convert to ViewBox coordinates
        local_top_left = QPointF(-offset_x, -offset_y)
        local_bottom_right = local_top_left + QPointF(raw_rect.width(), raw_rect.height())
        view_top_left = text_item.mapToView(local_top_left)
        view_bottom_right = text_item.mapToView(local_bottom_right)
        
        return QRectF(view_top_left, view_bottom_right)

    
    def background_box(self, text_item: TextItem, color: QColor = None) -> QGraphicsRectItem:
        """
        Creates a QGraphicsRectItem to serve as a background behind a TextItem.

        Parameters:
            text_item (TextItem): The text to draw the background behind.
            color (QColor, optional): Background color. If not provided, computed automatically.
        Returns:
            QGraphicsRectItem: The background box.
        """
        if color is None:
            color = self.get_background_color()
        bbox = self.bounding_box(text_item)

        # create QGraphicsRectItem
        bg_rect = QGraphicsRectItem(QRectF(0, 0, bbox.width(), bbox.height()))
        bg_rect.setBrush(mkBrush(color))  # fill color
        bg_rect.setPen(QPen(Qt.PenStyle.NoPen))  # line color

        # Set Z-value below that of the TextItem, which 
        # renders at Z = 0 regardless of what you set it to.
        # (I think due to pyqtgraph =/= PyQt)
        bg_rect.setZValue(-1)

        return bg_rect
    
    def get_background_color(self) -> QColor:
        """
        Returns the default background color for this label area.

        Applies blending and darkening to enhance visibility.

        Returns:
            QColor: The background color.
        """
        color = self.datawindow.composite_on_white(settings.get_label_color(self.label)) 
        color = color.darker(110) # 10% darker
        h, s, v, a = color.getHsvF()
        color = QColor.fromHsvF(h, min(1.0, s * 1.8), v, a) # up to 80% more saturated
        color.setAlpha(200)
        return color
            
    
    
    def update_label_area(self) -> None:
        """
        Redraws and repositions label area elements after zoom/pan or label changes.

        Called automatically on `sigTransformChanged` or manually after edits.
        """
        if not settings.get("show_labels"):
            return       
         
        self.viewbox = self.datawindow.viewbox
        _, (y_min, y_max) = self.viewbox.viewRange()

        centered_x = self.start_time + self.duration / 2
        label_y = y_min + 0.05 * (y_max - y_min)
        duration_y = y_max - 0.05 * (y_max - y_min)


        # update text and area if changed
        if self.label_text.toPlainText() != self.label:  # label changed
            self.label_text.setText(self.label)
            self.area.setBrush(mkBrush(color=settings.get_label_color(self.label)))
            self.label_background.setBrush(mkBrush(color=self.get_background_color()))
            self.duration_background.setBrush(mkBrush(color=self.get_background_color()))

        # if self.duration_text.toPlainText() != f"{self.duration:.2f}":  # duration changed
        self.duration_text.setText(f"{self.duration:.2f}")
        self.area.setRegion((self.start_time, self.start_time + self.duration))

        # update text pos
        self.label_text.setPos(centered_x, label_y)
        self.duration_text.setPos(centered_x, duration_y)

        # update text backgrounds
        self.label_bbox = self.bounding_box(self.label_text)
        self.duration_bbox = self.bounding_box(self.duration_text)
        
        self.update_rect(self.label_background, self.label_bbox)
        self.update_rect(self.duration_background, self.duration_bbox)

        if self.enable_debug:
            self.toggle_debug_boxes()
            # self.update_rect(self.label_debug_box, self.label_bbox)
            # self.update_rect(self.duration_debug_box, self.duration_bbox)
        else:
            self.toggle_debug_boxes()

        self.update_visibility()
        
    def update_rect(self, rect: QGraphicsRectItem, bbox: QRectF) -> None:
        """
        Updates a QGraphicsRectItem's geometry to match a QRectF.

        Parameters:
            rect (QGraphicsRectItem): The item to update.
            bbox (QRectF): The new bounding box.
        """
        rect.setRect(0, 0, bbox.width(), bbox.height())
        rect.setPos(bbox.topLeft())

    def update_visibility(self) -> None:
        """
        Hides the LabelArea if it is rendered <1px wide. If visible, it also hides the 
        label or duration text and backgrounds when they intersect a transition line (uses 
        opacity rather than visibilty to keep allow objects to keep updating.)

        Also checks whether to display duration text based on `settings.show_durations`.

        NOTE: hiding <1px can lead to multiple sequential short labels all being
        hidden, which can cause visible white regions, esp. when zoomed out.
        Not sure if there is a good fix for this, but it's pretty minor
        """


        window_x = lambda x: self.datawindow.viewbox_to_window(QPointF(x, 0)).x()
        label_width_px = abs(window_x(self.start_time + self.duration) - window_x(self.start_time))

        if label_width_px < 1:
            self.setVisible(False)     
            return
        elif not self.isVisible():
            self.setVisible(True)
    
        label_overlapping = self.label_bbox.left() < self.start_time < self.label_bbox.right()
        self.label_text.setOpacity(0.0 if  label_overlapping else 1.0)
        self.label_background.setOpacity(0.0 if  label_overlapping else 1.0)

        dur_overlapping = self.duration_bbox.left() < self.start_time < self.duration_bbox.right()        
        if settings.get("show_durations"):
            self.duration_text.setOpacity(0.0 if dur_overlapping else 1.0)
            self.duration_background.setOpacity(0.0 if dur_overlapping else 1.0)
        else:
            self.duration_text.setOpacity(0.0)
            self.duration_background.setOpacity(0.0)


    def getItems(self):
        """
        Returns:
            list: All graphical elements (area, line, texts, backgrounds, and optional debug items)
                that make up this LabelArea.
        """
        itemsToRemove = [
            self.area, self.transition_line, self.label_text, 
            self.duration_text,self.label_background, self.duration_background
        ]
        if self.right_transition_line is not None:
            itemsToRemove.append(self.right_transition_line)


        if self.datawindow.enable_debug:
            itemsToRemove.append(self.label_debug_box)
            itemsToRemove.append(self.duration_debug_box)

        return itemsToRemove


    def set_transition_line(self, line: Literal["left", "right"], x: float):
        """
        Moves the transition line to a new x-position.

        Parameters:
            x (float): The x-value to set the vertical transition line to.
        """
        if line == "left":
            self.transition_line.setValue(x)
            self.duration -= x - self.start_time
            self.start_time = x
        elif self.right_transition_line:
            self.right_transition_line.setValue(x)
            self.duration += x - (self.start_time + self.duration)
        self.update_label_area()


    def add_right_transition_line(self):
        if self.right_transition_line is not None:
            return
        self.right_transition_line = InfiniteLine(
            pos= self.start_time + self.duration,
            angle=90,  # vertical
            pen=mkPen(color=settings.get("plot_theme")["TRANSITION_LINE_COLOR"], width=2), # updated below
            hoverPen=None,
            movable=False,
        )
        self.viewbox.addItem(self.right_transition_line)
        selection = self.datawindow.selection
        if selection and selection.is_selected(self):
            self.right_transition_line.setPen(selection.selected_style['transition line'])
        elif selection.highlighted_item == self.right_transition_line:
            self.right_transition_line.setPen(selection.highlighted_style['transition line'])
        else:
            self.right_transition_line.setPen(selection.default_style['transition line'])

    def remove_right_transition_line(self):
        if self.right_transition_line is None:
            return
        self.viewbox.removeItem(self.right_transition_line)
        self.right_transition_line = None