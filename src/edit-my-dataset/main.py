#!/usr/bin/python3

import sys
import os
import json
from pathlib import Path
from collections import OrderedDict
import re

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QMessageBox, QGraphicsScene,
    QPushButton, QLabel, QHBoxLayout
)
from PyQt5.QtGui import QPixmap, QIcon, QKeySequence
from PyQt5.QtCore import Qt, QDir, QDirIterator
from PyQt5 import uic


def natural_sort_key(s):
    """Natural sorting for filenames (numbers in correct order)"""
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', str(s))]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("forms/mainwindow.ui", self)
        self.setWindowTitle("Edit My Dataset")

        # Data structures
        self.Map = OrderedDict()           # filename -> label (preserves order)
        self.LabelDict = {}                # label -> metadata (icon, etc.)
        self.validLabels = set()
        self.ButtonPtr = []
        self.Directory = QDir()
        self.CurrentImg = 0
        self.TotalImg = 0
        self.scene = None
        self.TypeIconSize = 48
        self.iconLabel = None

        self.strFilename = "filename"
        self.strLabel = "label"
        self.strSeparator = ","

        self.setup_ui()
        self.load_init_data()

    def setup_ui(self):
        """Connect all signals"""
        self.toolButton_Exit.clicked.connect(self.close)
        self.pushButton_Directory.clicked.connect(self.on_pushButton_Directory_clicked)
        self.pushButton_Csv.clicked.connect(self.on_pushButton_Csv_clicked)
        self.toolButton_Next.clicked.connect(self.on_toolButton_Next_clicked)
        self.toolButton_Previous.clicked.connect(self.on_toolButton_Previous_clicked)
        self.toolButton_Save.clicked.connect(self.on_toolButton_Save_clicked)
        self.pushButton_start.clicked.connect(self.on_pushButton_start_clicked)

        self.spinBox_ID.editingFinished.connect(self.on_spinBox_ID_editingFinished)

        # Icon inside lineEdit_Type
        self.iconLabel = QLabel(self.lineEdit_Type)
        self.iconLabel.setFixedSize(self.TypeIconSize, self.TypeIconSize)
        layout = QHBoxLayout(self.lineEdit_Type)
        layout.setContentsMargins(4, 0, 0, 0)
        layout.addWidget(self.iconLabel, 0, Qt.AlignLeft)
        layout.addStretch()
        self.lineEdit_Type.setLayout(layout)
        self.lineEdit_Type.setTextMargins(self.TypeIconSize + 8, 0, 0, 0)

    def load_init_data(self):
        """Load buttons and shortcuts from JSON"""
        home = Path.home()
        init_file = home / "edit-my-dataset.json"

        if not init_file.exists():
            self.create_default_file(init_file)

        try:
            with open(init_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            buttons = data.get("buttons", [])

            for btn_data in buttons:
                label = btn_data.get("button_label", "").strip()
                if not label:
                    continue

                self.validLabels.add(label)

                image_path = btn_data.get("button_image", "")
                width = btn_data.get("button_image_width", 0)
                shortcut = btn_data.get("short_cut", "").strip()

                # Resolve relative paths to home
                if image_path and not os.path.isabs(image_path):
                    image_path = str(home / image_path)

                button = QPushButton(label, self)
                button.setEnabled(False)

                if image_path and os.path.exists(image_path):
                    pixmap = QPixmap(image_path)
                    button.setIcon(QIcon(pixmap))
                    if width > 0:
                        button.setIconSize(pixmap.rect().size().scaled(width, 999, Qt.KeepAspectRatio))

                # Assign shortcut if available
                if shortcut:
                    button.setShortcut(QKeySequence(shortcut))

                # Click handler
                button.clicked.connect(lambda _, lbl=label: self.assign_label(lbl))

                self.verticalLayout_buttons.addWidget(button)
                self.ButtonPtr.append(button)

                # Store metadata
                self.LabelDict[label] = {
                    "button_image": image_path,
                    "button_image_width": width
                }

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load configuration:\n{e}")

    def create_default_file(self, filepath):
        """Create default JSON with buttons"""
        default = {
            "buttons": [
                {"button_label": "negative", "short_cut": "1"},
                {"button_label": "neutro", "short_cut": "2"},
                {"button_label": "pain", "short_cut": "3"},
                {"button_label": "positive", "short_cut": "4"},
                {"button_label": "unknown", "short_cut": "5"}
            ]
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=4, ensure_ascii=False)

    def assign_label(self, label: str):
        """Assign label to current image"""
        if not self.Map:
            return

        filename = list(self.Map.keys())[self.CurrentImg]
        self.Map[filename] = label

        self.statusbar.showMessage(f"Last image labeled: {label}", 4000)
        self.on_toolButton_Next_clicked()

    # ====================== SLOTS ======================

    def on_pushButton_Directory_clicked(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Root Directory")
        if directory:
            self.lineEdit_Directory.setText(directory)

    def on_pushButton_Csv_clicked(self):
        csvfile, _ = QFileDialog.getOpenFileName(
            self, "Open CSV File", "", "CSV Files (*.csv *.CSV)"
        )
        if csvfile:
            self.lineEdit_Csv.setText(csvfile)

    def on_spinBox_ID_editingFinished(self):
        val = self.spinBox_ID.value()
        if 0 <= val < self.TotalImg and val != self.CurrentImg:
            self.CurrentImg = val
            self.change_current_image()

    def on_toolButton_Next_clicked(self):
        if self.TotalImg == 0:
            return
        self.CurrentImg = (self.CurrentImg + 1) % self.TotalImg
        self.change_current_image()

    def on_toolButton_Previous_clicked(self):
        if self.TotalImg == 0:
            return
        self.CurrentImg = (self.CurrentImg - 1) % self.TotalImg
        self.change_current_image()

    def on_toolButton_Save_clicked(self):
        csv_path = self.lineEdit_Csv.text().strip()
        if not csv_path:
            QMessageBox.warning(self, "Warning", "No CSV file selected!")
            return

        has_header = self.checkBox_hasHeader.isChecked()

        try:
            with open(csv_path, "w", encoding="utf-8", newline="") as f:
                if has_header:
                    f.write(f"{self.strFilename}{self.strSeparator}{self.strLabel}\n")
                
                for filename, label in self.Map.items():
                    f.write(f"{filename}{self.strSeparator}{label}\n")

            QMessageBox.information(self, "Success", f"CSV file saved successfully:\n{csv_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def on_pushButton_start_clicked(self):
        csv_file = self.lineEdit_Csv.text().strip()
        root_dir = self.lineEdit_Directory.text().strip()

        if not csv_file or not os.path.exists(csv_file):
            QMessageBox.warning(self, "Error", "Please select a valid CSV file!")
            return
        if not root_dir or not os.path.exists(root_dir):
            QMessageBox.warning(self, "Error", "Please select a valid root directory!")
            return

        self.pushButton_start.setEnabled(False)
        QApplication.processEvents()

        self.Directory = QDir(root_dir)

        # Read CSV
        self.Map = self.read_csv_file(csv_file)

        if not self.Map:
            QMessageBox.warning(self, "Error", "CSV file is empty or invalid!")
            self.pushButton_start.setEnabled(True)
            return

        self.TotalImg = len(self.Map)
        self.CurrentImg = 0

        self.spinBox_ID.setMaximum(self.TotalImg - 1)
        self.progressBar.setMaximum(self.TotalImg)
        self.progressBar.setValue(0)
        self.progressBar.setFormat("Image %v of %m")

        # Validate labels
        invalid = []
        for i, (filename, label) in enumerate(self.Map.items()):
            if label.strip() and label.strip() not in self.validLabels:
                invalid.append(f"{filename} → {label}")
            self.progressBar.setValue(i)
            QApplication.processEvents()

        if invalid:
            QMessageBox.warning(self, "Invalid Labels",
                                "Some labels are not valid:\n\n" + "\n".join(invalid[:10]))

        # Enable controls
        for btn in self.ButtonPtr:
            btn.setEnabled(True)
        self.toolButton_Previous.setEnabled(True)
        self.toolButton_Next.setEnabled(True)
        self.toolButton_Save.setEnabled(True)

        QMessageBox.information(self, "Ready", f"Loaded {self.TotalImg} images.")
        self.change_current_image()
        self.pushButton_start.setEnabled(True)

    def read_csv_file(self, csv_path):
        """Read CSV maintaining natural order"""
        mapping = OrderedDict()
        if not os.path.exists(csv_path):
            return mapping

        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue

                parts = line.split(self.strSeparator, 1)
                if len(parts) >= 2:
                    filename = parts[0].strip()
                    label = parts[1].strip()
                    mapping[filename] = label
                elif i == 0 and self.checkBox_hasHeader.isChecked():
                    # Header row
                    if len(parts) >= 2:
                        self.strFilename = parts[0].strip()
                        self.strLabel = parts[1].strip()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to read CSV:\n{e}")

        return mapping

    def change_current_image(self):
        """Update UI with current image"""
        if not self.Map:
            return

        filename = list(self.Map.keys())[self.CurrentImg]
        label = self.Map[filename]

        full_path = self.Directory.filePath(filename)
        self.statusbar.showMessage(f"Image: {full_path}", 3000)

        # Load image
        if self.scene:
            self.scene.clear()
        else:
            self.scene = QGraphicsScene(self)
            self.graphicsView.setScene(self.scene)

        pixmap = QPixmap(full_path)
        if not pixmap.isNull():
            view_h = self.graphicsView.height()
            pixmap = pixmap.scaledToHeight(view_h, Qt.SmoothTransformation)
            self.scene.addPixmap(pixmap)

        # Update fields
        self.lineEdit_filename.setText(filename)
        self.spinBox_ID.setValue(self.CurrentImg)
        self.lineEdit_Type.setText(label)
        self.progressBar.setValue(self.CurrentImg)

        # Show label icon
        if label and label in self.LabelDict:
            icon_path = self.LabelDict[label]["button_image"]
            if icon_path and os.path.exists(icon_path):
                pix = QPixmap(icon_path).scaled(
                    self.TypeIconSize, self.TypeIconSize, Qt.KeepAspectRatio
                )
                self.iconLabel.setPixmap(pix)
            else:
                self.iconLabel.clear()
        else:
            self.iconLabel.clear()

    def closeEvent(self, event):
        reply = QMessageBox.question(self, "Exit", "Close the application?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
