from typing import Literal

from pyqtgraph import PlotWidget, InfiniteLine, mkPen, mkBrush

from PyQt6.QtGui import QColor, QMouseEvent, QKeyEvent
from PyQt6.QtCore import Qt, QPointF

from label_view.LabelArea import LabelArea
from settings import settings


# werid multi select bugs still, multi delete

class Selection:
    """
    Manages `DataWindow` selections and the actions performed on them.

    NOTE: More than one LabelArea can be selected at a time, but only a single 
    InfiniteLine can be directly selected.
    """
    def __init__(self, plot_widget: PlotWidget) -> None:
        """
        Initializes the selection manager for the given DataWindow (PlotWidget).

        Parameters:
            `plot_widget` (PlotWidget): The parent widget managing the label data and interactions.
        """

        self.selected_items: list = []  # InfiniteLine | LabelArea, sorted chronologically
        self.selection_parent: LabelArea = None  # which item is the "parent" of a multi-selection
        self.highlighted_item = None  # the item visually highlighted
        self.hovered_item = None  # the item the mouse is currently over
        self.dragged_line: InfiniteLine = None  # Which InfiniteLine (if any) is being dragged
        
        self.datawindow: PlotWidget = plot_widget  # the parent PlotWidget (i.e. the DataWindow)

        self.default_style = {
            'transition line': mkPen(color=settings.get("plot_theme")["TRANSITION_LINE_COLOR"], width=2),
            'baseline': mkPen(color='#808080', width=2),
            'text color': settings.get("plot_theme")["FONT_COLOR_1"]
        }

        self.highlighted_style = {
            'transition line' : mkPen(width=4, color='#0D6EFDC0'),
            'baseline' : mkPen(width=4, color='#0D6EFDC0'),
        }

        self.selected_style = {
            'transition line': mkPen(color='#0D6EFD', width=6),
            'baseline': mkPen(color="#031A3B", width=6),
            'area': mkBrush(color='#0D6EFD80'),  # label area LinearRegionItems
            'text background': mkBrush(color='#0D6EFD90'),  # label area text backgrounds
            'text color': "#FFFFFF"
        }

        self.moving_mode: bool = False

    def _sort_key(self, item) -> float:
        """
        Returns a key to sort selected items chronologically.

        Parameters:
            item (InfiniteLine | LabelArea): The item to derive the sort key from.

        Returns:
            float: The time value associated with the item.
        """
        if isinstance(item, LabelArea):
            return item.start_time
        if isinstance(item, InfiniteLine):
            return item.value()
        return float('inf')  # fallback
    
    def _update_default_style(self):
        # update for theme change
        self.default_style = {
            'transition line': mkPen(color=settings.get("plot_theme")["TRANSITION_LINE_COLOR"], width=2),
            'baseline': mkPen(color='#808080', width=2),
            'text color': settings.get("plot_theme")["FONT_COLOR_1"]
        }
    

    def select(self, item) -> None:
        """
        Adds the given item to the current selection and updates its visual style.

        Parameters:
            item (InfiniteLine | LabelArea): The item to select.
        """
        self.highlighted_item = None
        labels = self.datawindow.labels
        if isinstance(item, InfiniteLine):
            item.setPen(self.selected_style['transition line']) # same as highlighting currently
        if isinstance(item, LabelArea):
            if item.transition_line:
                item.transition_line.setPen(self.selected_style['transition line'])
                if item.transition_line not in self.selected_items:
                    self.selected_items.append(item.transition_line)

            idx = labels.index(item)
            if item.right_transition_line:
                item.right_transition_line.setPen(self.selected_style['transition line'])
                if item.right_transition_line not in self.selected_items:
                    self.selected_items.append(item.right_transition_line)
            elif idx + 1 < len(labels):
                next_label = labels[idx + 1]
                if next_label.transition_line:
                    next_label.transition_line.setPen(self.selected_style['transition line'])
                    if next_label.transition_line not in self.selected_items:
                        self.selected_items.append(next_label.transition_line)


            item.area.setBrush(self.selected_style['area'])
            item.label_text.setColor(self.selected_style['text color'])
            item.duration_text.setColor(self.selected_style['text color'])
            item.label_background.setBrush(self.selected_style['text background'])
            item.duration_background.setBrush(self.selected_style['text background'])


        self.selected_items.append(item)
        self.selected_items.sort(key=self._sort_key)
        self.datawindow.viewbox.update()

    
    def multi_select(self, item: LabelArea) -> None:
        """
        Selects all LabelAreas between the selection parent and the given item.

        Parameters:
            item (LabelArea): The target LabelArea that defines the other end of the selection range.
        """
        if self.selection_parent == None:  # fallback
            self.deselect_all()
            self.selection_parent = item
            self.select(item)

        labels = self.datawindow.labels[:] # shallow copy
        parent = self.selection_parent

        try:
            idx1 = labels.index(parent)
            idx2 = labels.index(item)
        except ValueError:
            return # one of the items isn't in the label list

        start_idx, end_idx = sorted((idx1, idx2))
        self.deselect_all()
        for i in range(start_idx, end_idx + 1):
            self.select(labels[i])
        self.selection_parent = parent

    def deselect_item(self, item: InfiniteLine | LabelArea) -> None:
        """
        Removes the item from selection and resets its visual style.

        Parameters:
            item (InfiniteLine | LabelArea): The item to deselect.
        """
        
        if isinstance(item, InfiniteLine) and item != self.highlighted_item:
            if item == self.datawindow.baseline:
                item.setPen(self.default_style['baseline'])
            else:
                item.setPen(self.default_style['transition line'])      

        if isinstance(item, LabelArea):
            labels = self.datawindow.labels
            idx = labels.index(item)

            item.area.setBrush(mkBrush(color=settings.get_label_color(item.label)))
            item.label_background.setBrush(mkBrush(item.get_background_color()))
            item.duration_background.setBrush(mkBrush(item.get_background_color()))
            item.label_text.setColor(self.default_style['text color'])
            item.duration_text.setColor(self.default_style['text color'])

            if item.transition_line and not self._is_line_shared(item.transition_line):
                item.transition_line.setPen(self.default_style['transition line'])

            if item.right_transition_line and not self._is_line_shared(item.right_transition_line):
                item.right_transition_line.setPen(self.default_style['transition line'])

        self.selected_items.remove(item)

    def _is_line_shared(self, line: InfiniteLine) -> bool:
        return sum(
            1 for item in self.selected_items 
            if isinstance(item, LabelArea) and (item.transition_line == line or item.right_transition_line == line)
        ) > 1

    def deselect_all(self) -> None:
        """
        Clears the current selection and resets all selected item styles.
        """
        for item in self.selected_items[:]:
            self.deselect_item(item)
        self.selection_parent = None
    
    def is_selected(self, item) -> bool:
        """
        Checks whether the given item is currently selected.

        Parameters:
            item (InfiniteLine | LabelArea): The item to check.

        Returns:
            bool: True if the item is in the current selection, otherwise False.
        """
        if isinstance(item, LabelArea):
            return item in self.selected_items
        if isinstance(item, InfiniteLine):
            return item in self.get_selected_lines()
        return False

    def get_selected_lines(self) -> list[InfiniteLine]:
        """
        Gets a list of InfiniteLines associated with the current selection.

        Returns:
            list[InfiniteLine]: All selected InfiniteLines, including those adjacent to selected LabelAreas.
        """

        lines = []
        for item in self.selected_items:
            if isinstance(item, InfiniteLine):
                lines.append(item)
            elif isinstance(item, LabelArea):
                if item.transition_line:
                    lines.append(item.transition_line)
                if item.right_transition_line:
                    lines.append(item.right_transition_line)
        return lines

    def key_press_event(self, event: QKeyEvent) -> None:
        """
        Handles keyboard actions on selection.

        If Delete or Backspace is pressed, deletes selected label areas with merge behavior on edge labels.

        Parameters:
            event (QKeyEvent): The key press event.
        """
        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            label_areas_to_delete = [item for item in self.selected_items if isinstance(item, LabelArea)][::-1]
            self.deselect_all()

            for label_area in label_areas_to_delete:
                if label_area != label_areas_to_delete[-1]:
                    self.delete_label_area(label_area)
                else:
                    self.delete_label_area(label_area)

    def mouse_press_event(self, event: QMouseEvent) -> None:
        """
        Handles mouse click selection logic, including Shift and Ctrl modifiers.

        - Left-click selects or deselects items.
        - Shift-click performs range multi-selection.
        - Ctrl-click toggles individual label area selection.

        Parameters:
            event (QMouseEvent): The mouse click event.
        """
        point = self.datawindow.window_to_viewbox(event.position())
        x, y = point.x(), point.y()

        (x_min, x_max), (y_min, y_max) = self.datawindow.viewbox.viewRange()
        if not (x_min <= x <= x_max and y_min <= y <= y_max):
            self.deselect_all()
            self.datawindow.scene().update()
            return
        
        # ----------- LEFT CLICK -----------
        if event.button() == Qt.MouseButton.LeftButton:
            #COMMENT TESITNG
            if self.datawindow.comment_editing:
                self.datawindow.comment_editing = False
                return

            # Left-clicked no item
            if self.hovered_item == None:
                self.deselect_all()

            # Left-clicked InfiniteLine 
            elif isinstance(self.hovered_item, InfiniteLine):
                if not self.is_selected(self.hovered_item):
                    self.deselect_all()
                    self.select(self.hovered_item)  

                self.dragged_line = self.hovered_item
                self.moving_mode = True
                self.datawindow.setCursor(Qt.CursorShape.ClosedHandCursor)

            # Left-clicked LabelArea
            elif isinstance(self.hovered_item, LabelArea):
                # ---- Normal click -------
                if event.modifiers() == Qt.KeyboardModifier.NoModifier:
                    self.deselect_all()
                    self.select(self.hovered_item)
                    self.selection_parent = self.hovered_item

                # ---- Shift-click --------
                elif event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    if all(isinstance(item, InfiniteLine) for item in self.selected_items):
                        self.deselect_all()  # only label areas can have multi selection
                    if not self.selected_items:
                        self.select(self.hovered_item)
                        self.selection_parent = self.hovered_item
                    else:
                        self.multi_select(self.hovered_item)                        

                # ---- Ctrl-click ---------
                elif event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    if all(isinstance(item, InfiniteLine) for item in self.selected_items):
                        self.deselect_all()  # only label areas can have multi selection
                    if not self.is_selected(self.hovered_item):
                        self.select(self.hovered_item)
                        self.selection_parent = self.hovered_item
                    else:
                        self.deselect_item(self.hovered_item)
                
    def mouse_move_event(self, event: QMouseEvent) -> None:
        """
        Handles hover highlighting and transition line dragging on mouse movement.

        Parameters:
            event (QMouseEvent): The mouse move event.
        """
        point = self.datawindow.window_to_viewbox(event.position())
        x, y = point.x(), point.y()

        if self.datawindow.edit_mode_enabled and not self.moving_mode:
            self.hover(x, y) 
            self.datawindow.scene().update()
        elif self.moving_mode and self.dragged_line is not None:
            self.apply_drag(x, y)
        return
                
    def mouse_release_event(self, event: QMouseEvent) -> None:
        """
        Finalizes a drag operation and updates styling after releasing the mouse button.

        Parameters:
            event (QMouseEvent): The mouse release event.
        """
        point = self.datawindow.window_to_viewbox(event.position())
        x, y = point.x(), point.y()

        if not self.dragged_line:
            return 
        
        if self.moving_mode:
            self.hover(x,y)
            if self.dragged_line == self.datawindow.baseline:
                # Place baseline
                self.dragged_line.setPen(self.highlighted_style['baseline'])
                self.highlighted_item = self.dragged_line
                self.deselect_item(self.dragged_line)
            else:
                # Get the index of the label area the dragged line belongs to
                labels = self.datawindow.labels
                idx = None
                for i, label_area in enumerate(labels):
                    if (
                        label_area.transition_line == self.dragged_line
                        or label_area.right_transition_line == self.dragged_line
                    ):
                        idx = i

                if idx is not None:
                    if labels[idx].transition_line == self.dragged_line:
                        left_area_selected = self.is_selected(labels[idx - 1]) if idx > 0 else False
                        right_area_selected = self.is_selected(labels[idx]) if idx < len(labels) else False
                    else:
                        left_area_selected = self.is_selected(labels[idx])
                        right_area_selected = False # no right area if right transition line exists

                    if not (left_area_selected or right_area_selected) and self.dragged_line == self.hovered_item:
                        self.dragged_line.setPen(self.highlighted_style['transition line'])
                        self.highlighted_item = self.dragged_line
                        self.deselect_item(self.dragged_line)
                self._attempt_snap_and_merge(self.dragged_line)
                
            self.moving_mode = False
            self.dragged_line = None
            self.datawindow.setCursor(Qt.CursorShape.OpenHandCursor)
        return

    def _attempt_snap_and_merge(self, line: InfiniteLine) -> None:
        """
        If the given transition line is near a neighbor's transition line, snap to it and merge if labels match.
        
        Parameters:
            line (InfiniteLine): The line being released after dragging.
        """
        SNAP_THRESHOLD = 2 * self.datawindow.devicePixelRatioF()
        labels = self.datawindow.labels
        idx = None
        line_type = None

        for i, label in enumerate(labels):
            if label.transition_line == line:
                idx = i
                line_type = 'left'
                break
            elif label.right_transition_line == line:
                idx = i
                line_type = 'right'
                break

        if idx is None:
            return  # line not associated with a label
    

        if line_type == "left" and idx > 0:
            left = labels[idx - 1]
            right = labels[idx]
            left_end = left.start_time + left.duration
            right_start = right.start_time

            # Compute the gap in viewbox coordinates
            vb_x = lambda x: self.datawindow.viewbox_to_window(QPointF(x ,0)).x() 
            view_dist = abs(vb_x(left_end) - vb_x(right_start))

            if abs(view_dist - SNAP_THRESHOLD) <= 1e-6:
                # Snap
                right.start_time = left_end
                right.duration = (right_start + right.duration) - right.start_time
                right.set_transition_line("left", left_end)
                left.update_label_area()

                # Merge if needed
                self.merge_adjacent_labels(right)
                self.datawindow.update_right_transition_lines()

        elif line_type == "right" and idx + 1 < len(labels):
            left = labels[idx]
            right = labels[idx + 1]
            left_end = left.start_time + left.duration
            right_start = right.start_time

            # Compute the gap in viewbox coordinates
            vb_x = lambda x: self.datawindow.viewbox_to_window(QPointF(x ,0)).x() 
            view_dist = abs(vb_x(left_end) - vb_x(right_start))

            if view_dist - SNAP_THRESHOLD <= 1e-6:
                # Snap
                left.duration = right_start - left.start_time
                left.set_transition_line("right", right_start)

                # Merge if needed
                self.merge_adjacent_labels(left)   
                self.datawindow.update_right_transition_lines()
        
    def apply_drag(self, x: float, y: float) -> None:
        """
        Applies dragging motion to a transition line or baseline, updating LabelArea boundaries.

        Parameters:
            x (float): The ViewBox x-coordinate.
            y (float): The ViewBox y-coordinate.
        """
        line = self.dragged_line
        if line is None:
            return

        if line == self.datawindow.baseline:
            self.datawindow.baseline.setPos(y)
            return

        labels = self.datawindow.labels
        for i, label in enumerate(labels):
            if label.transition_line == line:
                self._apply_drag_transition(i, x, which_line='left')
                return
            elif label.right_transition_line == line:
                self._apply_drag_transition(i, x, which_line='right')
                return
    
    
    def _apply_drag_transition(self, index: int, x: float, which_line: Literal['left', 'right']) -> None:
        labels = self.datawindow.labels
        viewbox = self.datawindow.viewbox
        MIN_PIXEL_DISTANCE = 2 * self.datawindow.devicePixelRatioF()

        # Compute the minimum gap in viewbox coordinates
        vb_x = lambda x: self.datawindow.window_to_viewbox(QPointF(x ,0)).x() 
        min_vb_distance = vb_x(MIN_PIXEL_DISTANCE) - vb_x(0)

        if which_line == 'left':
            left = labels[index - 1] if index > 0 else None
            right = labels[index]
            left_end = left.start_time + left.duration if left else 0
            right_end = right.start_time + right.duration

            touching = abs(left_end - right.start_time) < 1e-9  # exact match

            if touching and index > 0:
                min_x = left.start_time + min_vb_distance if index != 0 else 0
                max_x = right_end - min_vb_distance
                clamped_x = max(min_x, min(x, max_x))


                left.duration = clamped_x - left.start_time
                right.start_time = clamped_x
                right.duration = right_end - clamped_x
            else:
                min_x = left_end + min_vb_distance if index != 0 else 0
                max_x = right_end - min_vb_distance
                clamped_x = max(min_x, min(x, max_x))

                right.start_time = clamped_x
                right.duration = right_end - clamped_x

            right.set_transition_line("left", clamped_x)
            if left:
                left.update_label_area()

        elif which_line == 'right':
            left = labels[index]
            right = labels[index + 1] if index + 1 < len(labels) else None

            left_end = left.start_time + left.duration
            right_start = right.start_time if right else float('inf')

            touching = right and abs(left_end - right_start) < 1e-9

            if touching:
                # Right line is shared
                min_x = left.start_time + min_vb_distance
                max_x = right_start + right.duration - min_vb_distance
                clamped_x = max(min_x, min(x, max_x))

                left.duration = clamped_x - left.start_time
                right.start_time = clamped_x
                right.duration = (right_start + right.duration) - clamped_x

                right.set_transition_line("left", clamped_x)

            else:
                # Right line is local to `left`
                min_x = left.start_time + min_vb_distance
                max_x = right_start - min_vb_distance if right else float('inf')
                clamped_x = max(min_x, min(x, max_x))

                left.duration = clamped_x - left.start_time

            left.set_transition_line("right", clamped_x)


    def delete_label_area(self, label_area: LabelArea) -> None:
        """
        Deletes a LabelArea in place, ensuring the left neighbor 
        receives a right_transition_line, if it exists.

        Parameters:
            label_area (LabelArea): The LabelArea to delete.
            multi_delete (bool): Whether a multi-selection is being deleted.
        """
        labels = self.datawindow.labels
        idx = labels.index(label_area)

        # Update left neighbor to add right_transition_line
        if idx > 0:
            left_neighbor = labels[idx - 1]
            if not left_neighbor.right_transition_line:
                x = label_area.start_time + label_area.duration
                left_neighbor.add_right_transition_line()

        
        # Remove all visual elements
        for item in label_area.getItems():
            scene = item.scene()
            if scene:
                scene.removeItem(item)

        if self.is_selected(label_area):
            self.deselect_item(label_area)

        self.datawindow.labels.remove(label_area)

        if self.datawindow.last_cursor_pos:
            view_pos = self.datawindow.window_to_viewbox(self.datawindow.last_cursor_pos)
            self.hover(view_pos.x(), view_pos.y())

    def merge_adjacent_labels(self, label_area: LabelArea, deleting = False) -> bool:
        """
        Merges the given LabelArea with adjacent ones if they are of the same type
        and are exactly adjacent (no gap between them).

        Parameters:
            label_area (LabelArea): The LabelArea to merge from.
            deleting (bool): True if the merge is happening as part of a deletion.
        Returns:
            (bool): Whether a merge was performed.
        """
        labels = self.datawindow.labels
        if not labels:
            return
        
        idx = labels.index(label_area)
        before = labels[idx - 1] if idx > 0 else None
        after = labels[idx + 1] if idx + 1 < len(labels) else None

        if deleting:
            after = None  # dont merge right on deletion


        epsilon = 1e-9
        merging_left = (
            before and
            before.label == label_area.label and
            abs((before.start_time + before.duration) - label_area.start_time) < epsilon
        )
        merging_right = (
            after and
            after.label == label_area.label and
            abs((label_area.start_time + label_area.duration) - after.start_time) < epsilon
        )

        def remove_label_area(area: LabelArea) -> None:
            """Helper function to remove label areas from the viewbox and update labels."""
            for item in area.getItems():
                scene = item.scene()
                if scene is not None:
                    scene.removeItem(item)

            if area in self.datawindow.labels:
                if self.is_selected(area):
                    self.deselect_item(area)
                self.datawindow.labels.remove(area)

        if merging_left and merging_right:
            if self.is_selected(label_area):
                self.select(before)

            remove_label_area(label_area)
            remove_label_area(after)

            before.duration += + label_area.duration + after.duration
            before.update_label_area()

            if before.right_transition_line:
                before.remove_right_transition_line()

        elif merging_left:
            if self.is_selected(label_area):
                self.select(before)

            remove_label_area(label_area)
            before.duration +=  label_area.duration
            before.update_label_area()

            if before.right_transition_line:
                before.remove_right_transition_line()

        elif merging_right:
            remove_label_area(after)
            label_area.duration += after.duration
            label_area.update_label_area()

            if label_area.right_transition_line:
                label_area.remove_right_transition_line()

        if self.datawindow.last_cursor_pos:
            view_pos = self.datawindow.window_to_viewbox(self.datawindow.last_cursor_pos)
            self.hover(view_pos.x(), view_pos.y())

        return merging_left or merging_right

    def hover(self, x: float, y: float) -> None:
        """
        Updates the hovered and highlighted item based on cursor position.

        Parameters:
            x (float): The ViewBox x-coordinate.
            y (float): The ViewBox y-coordinate.
        """
        (x_min, x_max), (y_min, y_max) = self.datawindow.viewbox.viewRange()

        if not (x_min <= x <= x_max and y_min <= y <= y_max):  # cursor outside viewbox
            if self.highlighted_item is not None:
                self.unhighlight_item(self.highlighted_item)
            self.datawindow.setCursor(Qt.CursorShape.ArrowCursor)
            return

        item_to_highlight = self.get_hovered_item(x ,y)

        cursor = None
        if isinstance(item_to_highlight, InfiniteLine):
            cursor = Qt.CursorShape.OpenHandCursor

        self.update_highlight(item_to_highlight, cursor=cursor)

    def get_hovered_item(self, x: float, y: float) -> InfiniteLine | LabelArea | None:
        """
        Determines the item under the cursor for highlighting or interaction.

        Parameters:
            x (float): ViewBox x-coordinate.
            y (float): ViewBox y-coordinate.

        Returns:
            (InfiniteLine | LabelArea | None): The item nearest the cursor, or None if nothing should be highlighted.
        """
        TRANSITION_HIGHLIGHT_THRESHOLD = 3 * self.datawindow.devicePixelRatioF()
        BASELINE_HIGHLIGHT_THRESHOLD = 3 * self.datawindow.devicePixelRatioF()

        # Get distances to relevant items
        transition_line, transition_distance = self.datawindow.get_closest_transition(x)
        baseline, baseline_distance = self.datawindow.get_baseline_distance(y)
        label_area = self.datawindow.get_closest_label_area(x)

        if not self.datawindow.baseline.isVisible():
            baseline_distance = float('inf')

        if transition_distance <= TRANSITION_HIGHLIGHT_THRESHOLD:
            hovered_item = transition_line

        elif baseline_distance <= BASELINE_HIGHLIGHT_THRESHOLD:
            hovered_item = baseline

        elif label_area is not None:
            # Only highlight label area if cursor is inside it
            if label_area.start_time <= x <= label_area.start_time + label_area.duration:
                hovered_item = label_area
            else:
                hovered_item = None
        else:
            hovered_item = None

        self.hovered_item = hovered_item
        return hovered_item



    def update_highlight(self, item, cursor: Qt.CursorShape = None) -> None:
        """
        Highlights the specified item and sets the appropriate cursor.

        Parameters:
            item (InfiniteLine | LabelArea): The item to highlight.
            cursor (Qt.CursorShape, optional): The cursor to display.
        """
        if cursor:
            self.datawindow.setCursor(cursor)
        else:
            self.datawindow.setCursor(Qt.CursorShape.ArrowCursor)  # default

        if self.is_selected(item):
            self.unhighlight_item(self.highlighted_item) # unhighlight previous item
            return  # don't highlight already selected items

        # Check if highlighted item needs to change:
        if self.highlighted_item != item:
            if self.highlighted_item is not None:
                self.unhighlight_item(self.highlighted_item) # unhighlight previous item
    
            if isinstance(item ,InfiniteLine):
                if item == self.datawindow.baseline:
                    item.setPen(self.highlighted_style['baseline'])
                else:
                    item.setPen(self.highlighted_style['transition line'])

            elif isinstance(item, LabelArea):
                label_area_color = self.datawindow.composite_on_white(settings.get_label_color(item.label))
                text_background_color = item.label_background.brush().color()

                highlighted_area_color = self.get_highlighted_color(label_area_color)
                highlighted_background_color = self.get_highlighted_color(text_background_color)
                item.area.setBrush(mkBrush(color=highlighted_area_color))
                item.label_background.setBrush(mkBrush(highlighted_background_color))
                item.duration_background.setBrush(mkBrush(highlighted_background_color))

            self.highlighted_item = item

    def get_highlighted_color(self, color: QColor) -> QColor:
        """
        Generates a visually emphasized color for hover/highlight feedback.

        Parameters:
            color (QColor): The base color.

        Returns:
            QColor: The modified highlighted color.
        """
        h, s, l, a = color.getHslF()
        l_scaler = 0.9 if settings.get("plot_theme")["NAME"] == "LIGHT" else 1.6
        highlighted_color = QColor.fromHslF(h, max(s, 1 - s**2), l * l_scaler, a)    
        highlighted_color.setAlpha(200)
        return highlighted_color

    def unhighlight_item(self, item) -> None:
        """
        Resets the style of the currently highlighted item.

        Parameters:
            item (InfiniteLine | LabelArea): The item to unhighlight.
        """
        if isinstance(item ,InfiniteLine):
            if item == self.datawindow.baseline:
                item.setPen(self.default_style['baseline'])
            else:
                item.setPen(self.default_style['transition line'])
        if isinstance(item, LabelArea):
            item.area.setBrush(mkBrush(color=settings.get_label_color(item.label)))
            item.label_background.setBrush(mkBrush(color=item.get_background_color()))
            item.duration_background.setBrush(mkBrush(color=item.get_background_color()))

        self.highlighted_item = None

    def change_label_type(self, label_area: LabelArea, new_label: str) -> None:
        """
        Changes the label type for the given LabelArea (or all selected ones) and merges if applicable.

        Parameters:
            label_area (LabelArea): The LabelArea to modify.
            new_label (str): The new label type to assign.
        """
        dw = self.datawindow
        merged = False  # whether a merge was performed

        if self.is_selected(label_area): # label area is selected
            selected_label_areas = [label for label in self.selected_items if isinstance(label, LabelArea)]
            for label_area in selected_label_areas: # change without merging
                label_area.label = new_label
                label_area.update_label_area()
                label_area.area.setBrush(self.selected_style['area'])
                label_area.label_background.setBrush(self.selected_style['text background'])
                label_area.duration_background.setBrush(self.selected_style['text background'])

            for label_area in selected_label_areas[:]: # merge all labels if necessary
                if label_area in self.datawindow.labels:
                    did_merge = self.merge_adjacent_labels(label_area)
                    merged = merged or did_merge
        else: # label area is highlighted
            label_area.label = new_label
            label_area.update_label_area()
            merged = self.merge_adjacent_labels(label_area)

        dw.viewbox.update()

        if merged:
            # kind of brute force, can we make this only update the necessary point in the df?
            transitions = [(label_area.start_time, label_area.label) for label_area in dw.labels]
            dw.epgdata.set_transitions(dw.file, transitions, dw.transition_mode)