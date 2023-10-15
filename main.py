import sys
import os
import json
import requests
from bs4 import BeautifulSoup
import urllib.parse
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLineEdit, QPushButton, QLabel, QFileDialog, QTextEdit, QDialog, QFormLayout, QSpinBox, QComboBox
from PyQt5.QtGui import QPalette, QColor, QIcon, QFontDatabase, QFont
from PyQt5.QtCore import Qt

# https://stackoverflow.com/questions/31836104/pyinstaller-and-onefile-how-to-include-an-image-in-the-exe-file

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")

        self.layout = QFormLayout()

        self.download_threads_label = QLabel("Download Threads:")
        self.layout.addRow(self.download_threads_label)

        # Add a spin box to set the number of download threads
        self.download_threads_spinbox = QSpinBox()
        self.download_threads_spinbox.setRange(1, 32)  # Adjust the range as needed
        self.layout.addRow(self.download_threads_spinbox)

        self.default_download_label = QLabel("Default Download Location:")
        self.layout.addRow(self.default_download_label)

        self.default_download_entry = QLineEdit()
        self.default_download_entry.setStyleSheet("color: white; background-color: #333333;")
        self.layout.addRow(self.default_download_entry)

        self.theme_label = QLabel("Theme:")
        self.layout.addRow(self.theme_label)

        # Add a combo box to select themes
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Dark Theme")
        self.theme_combo.addItem("Light Theme")
        self.theme_combo.addItem("Space Theme")
        self.layout.addRow(self.theme_combo)

        # Load and apply settings
        self.load_settings()

        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_settings)
        self.layout.addRow(self.save_button)

        self.setLayout(self.layout)

    def load_settings(self):
        # Load settings from a JSON file in the "config" folder
        settings_path = os.path.join("config", "settings.json")
        if os.path.exists(settings_path):
            with open(settings_path, "r") as settings_file:
                settings = json.load(settings_file)
                download_threads = settings.get("download_threads", 1)
                default_download_location = settings.get("default_download_location", "")
                theme = settings.get("theme", 0)  # Default to dark theme
                self.download_threads_spinbox.setValue(download_threads)
                self.default_download_entry.setText(default_download_location)
                self.theme_combo.setCurrentIndex(theme)  # Set the selected theme

    def save_settings(self):
        # Save settings to a JSON file in the "config" folder
        settings_path = os.path.join("config", "settings.json")
        download_threads = self.download_threads_spinbox.value()
        default_download_location = self.default_download_entry.text()
        theme = self.theme_combo.currentIndex()  # Get the selected theme
        settings = {
            "download_threads": download_threads,
            "default_download_location": default_download_location,
            "theme": theme  # Save the selected theme
        }
        with open(settings_path, "w") as settings_file:
            json.dump(settings, settings_file)
        self.accept()
        self.parent().apply_theme(theme)  # Apply the selected theme

class ArchiveDownloader(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Internet Archive Downloader")
        self.setGeometry(100, 100, 600, 400)

        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout()

        # Use Bebas Neue font from the "fonts" folder
        font_path = os.path.join("fonts", "BebasNeue-Regular.ttf")
        QFontDatabase.addApplicationFont(font_path)
        bebas_neue_font = QFont("Bebas Neue", 12)

        self.url_label = QLabel("Internet Archive URL:")
        self.url_label.setFont(bebas_neue_font)
        self.url_label.setStyleSheet("color: white;")
        self.layout.addWidget(self.url_label)

        self.url_entry = QLineEdit()
        self.url_entry.setFont(bebas_neue_font)
        self.url_entry.setStyleSheet("color: white; background-color: #333333;")
        self.layout.addWidget(self.url_entry)

        self.folder_label = QLabel("Download Folder:")
        self.folder_label.setFont(bebas_neue_font)
        self.folder_label.setStyleSheet("color: white;")
        self.layout.addWidget(self.folder_label)

        self.folder_entry = QLineEdit()
        self.folder_entry.setFont(bebas_neue_font)
        self.folder_entry.setStyleSheet("color: white; background-color: #333333;")
        self.layout.addWidget(self.folder_entry)

        self.browse_button = QPushButton("Browse")
        self.browse_button.setFont(bebas_neue_font)
        self.browse_button.setStyleSheet("color: white; background-color: #333333;")
        self.browse_button.clicked.connect(self.choose_folder)
        self.layout.addWidget(self.browse_button)

        self.settings_button = QPushButton("Settings")  # Add a Settings button
        self.settings_button.setFont(bebas_neue_font)
        self.settings_button.setStyleSheet("color: white; background-color: #333333;")
        self.settings_button.clicked.connect(self.open_settings_dialog)
        self.layout.addWidget(self.settings_button)

        self.download_button = QPushButton("Download")
        self.download_button.setFont(bebas_neue_font)
        self.download_button.setStyleSheet("color: white; background-color: #333333;")
        self.download_button.clicked.connect(self.scrape_and_download)
        self.layout.addWidget(self.download_button)

        self.status_label = QTextEdit()
        self.status_label.setFont(bebas_neue_font)
        self.status_label.setStyleSheet("color: white; background-color: #333333;")
        self.status_label.setReadOnly(True)
        self.layout.addWidget(self.status_label)

        self.central_widget.setLayout(self.layout)

        # Set the application icon from the "assets" folder
        icon_path = os.path.join("assets", "icon.png")
        icon = QIcon(icon_path)
        self.setWindowIcon(icon)

        # Load settings and theme from configuration files
        self.load_settings()
        self.apply_theme(self.get_current_theme())

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Download Folder")
        self.folder_entry.setText(folder)

    def scrape_and_download(self):
        url = self.url_entry.text()
        download_folder = self.folder_entry.text()

        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            for link in soup.find_all('a'):
                href = link.get('href')
                if href and '/download/' in href:
                    download_link = urllib.parse.urljoin(url, href)
                    self.download_file(download_link, download_folder)

    def download_file(self, url, download_folder):
        filename = os.path.join(download_folder, os.path.basename(url))
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(filename, 'wb') as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)
            self.status_label.append(f"Downloaded: {filename}")
        else:
            self.status_label.append(f"Failed to download: {url}")

    def load_settings(self):
        # Load settings from a JSON file in the "config" folder
        settings_path = os.path.join("config", "settings.json")
        if os.path.exists(settings_path):
            with open(settings_path, "r") as settings_file:
                settings = json.load(settings_file)
                # Use the loaded settings as needed

    def get_current_theme(self):
        # Load theme settings from a JSON file in the "config" folder
        theme_path = os.path.join("config", "theme.json")
        if os.path.exists(theme_path):
            with open(theme_path, "r") as theme_file:
                theme = json.load(theme_file)
                return theme.get("theme", 0)  # Default to dark theme
        return 0  # Default to dark theme if no theme file

    def open_settings_dialog(self):
        dialog = SettingsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            # Reload settings and apply changes
            self.load_settings()
            self.apply_theme(dialog.theme_combo.currentIndex())  # Apply the selected theme

    def apply_theme(self, theme_index):
        # Load theme settings from the "theme.json" file
        theme_path = os.path.join("config", "theme.json")
        if os.path.exists(theme_path):
            with open(theme_path, "r") as theme_file:
                theme_data = json.load(theme_file)
                themes = theme_data.get("themes", {})
                selected_theme = themes.get("dark", {})  # Default to Dark Theme

                if theme_index == 1:
                    selected_theme = themes.get("light", {})

                palette = QPalette()
                palette.setColor(QPalette.Window, QColor(selected_theme.get("background_color", "#FFFFFF")))
                palette.setColor(QPalette.WindowText, QColor(selected_theme.get("text_color", "#000000")))
                palette.setColor(QPalette.Button, QColor(selected_theme.get("button_color", "#0077FF")))
                self.setPalette(palette)

                # Adjust the text color of input fields to black
                self.url_entry.setStyleSheet("color: black; background-color: white;")
                self.folder_entry.setStyleSheet("color: black; background-color: white")

def main():
    app = QApplication(sys.argv)
    window = ArchiveDownloader()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
