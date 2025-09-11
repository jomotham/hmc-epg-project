from settings.SettingsWindow import SettingsWindow
from settings import settings

if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    lc = {'N': {'LIGHT': '#f6e9c2', 'DARK': '#2d260f'}, 'P': {'LIGHT': '#f4dbc4', 'DARK': '#2c1e10'}, 'Z': {'LIGHT': '#bafed3', 'DARK': '#083418'}, 'B2': {'LIGHT': '#bbedfd', 'DARK': '#082934'}, 'C': {'LIGHT': '#f9f7bf', 'DARK': '#302f0c'}, 'D': {'LIGHT': '#c4f4e7', 'DARK': '#102c24'}, 'F2': {'LIGHT': '#c3eef5', 'DARK': '#0f282d'}, 'B': {'LIGHT': '#bafeef', 'DARK': '#08342a'}, 'FB': {'LIGHT': '#cef3c5', 'DARK': '#162a12'}, 'F1': {'LIGHT': '#c2dcf6', 'DARK': '#0f1e2d'}, 'G': {'LIGHT': '#c7eef1', 'DARK': '#132729'}}
    settings.set("label_colors", lc)
    window = SettingsWindow()

    window.show()
    sys.exit(app.exec())