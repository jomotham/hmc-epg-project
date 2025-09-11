import os
import re
#import sys

from PyQt6.QtWidgets import QFileDialog,QMessageBox, QDialog

from label_view.DataWindow import DataWindow
from utils.WindaqFileDialog import WindaqFileDialog
from EPGData import EPGData

class FileSelector:
    def load_new_data(epgdata: EPGData, datawindow) -> None:
        if not datawindow.checkForUnsavedChanges():
            msg_box = QMessageBox(datawindow)
            msg_box.setWindowTitle("Unsaved Changes in Label View")
            msg_box.setText("You have unsaved changes in Label View. Do you want to save them before opening another file?")

            msg_box.setStandardButtons(QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
            msg_box.setDefaultButton(QMessageBox.StandardButton.Save)

            reply = msg_box.exec()

            if reply == QMessageBox.StandardButton.Save:
                export_successful = datawindow.export_df() 
                if not export_successful:
                    return
            elif reply == QMessageBox.StandardButton.Discard:
                pass # proceed with opening new file w/o save
            else:
                # cancel opening new file
                return
        datawindow.transition_mode = 'labels'
        file_dialog = QFileDialog()
             
        file_path, _ = file_dialog.getOpenFileUrl()
        file_path = file_path.toLocalFile()
        channel_idx = None
        if file_path:
            if os.path.splitext(file_path)[1].lower() in [".wdq", ".daq", '.wdh']:
                windaq_dialog = WindaqFileDialog(file_path)
                if windaq_dialog.exec() == QDialog.DialogCode.Accepted:
                    channel_idx = windaq_dialog.get_selected_channel_index()
                else:
                    print("WinDAQ channel selection cancelled.")
                    return
            if epgdata.load_data(file_path, channel_idx) and isinstance(datawindow, DataWindow):
                datawindow.plot_recording(file_path)
                #datawindow.plot_transitions(file_path)
                #datawindow.mode = 'labels'
                #datawindow.plot_comments(file_path)

    def export_labeled_data(epgdata: EPGData, file: str):
        file_dialog = QFileDialog()
        file_dialog.AcceptMode = 1 # save mode
        file_url, selected_filter = file_dialog.getSaveFileUrl(filter="CSV files (*.csv);;text files (*.txt)")
        file_path = file_url.toLocalFile()
        if selected_filter:
            extension = re.match(r'^.*\(\*\.(.*)\)$', selected_filter).group(1)
        if file_path:
            dirname  = os.path.dirname(file_path)
            basename = os.path.basename(file_path)
            # NOTE: not sure if it's a misuse of the filter to use it to force the extension,
            # rather than just using it to limit what files are visible in the dialog
            if '.' in basename:
                if basename.rsplit(".", 1)[1] != extension:
                    basename = basename.rsplit(".", 1)[0] + '.' + extension
            else:
                basename += '.' + extension
            full_path = os.path.join(dirname, basename)
            if extension.lower() == 'csv':
                epgdata.export_csv(file, full_path)
            elif extension.lower() == 'txt':
                epgdata.export_txt(file, full_path)

