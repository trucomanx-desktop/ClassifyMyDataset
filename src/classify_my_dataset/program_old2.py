#!/usr/bin/python3

import sys
import os
import json
from pathlib import Path
from collections import OrderedDict
import re

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QMessageBox, QGraphicsScene,
    QPushButton, QLabel, QHBoxLayout, QVBoxLayout, QFormLayout, QGridLayout,
    QToolButton, QLineEdit, QSpinBox, QCheckBox, QProgressBar, QGraphicsView,
    QMenuBar, QMenu, QAction, QSizePolicy, QSpacerItem, QWidget
)
from PyQt5.QtGui import QPixmap, QIcon, QKeySequence, QFont
from PyQt5.QtCore import Qt, QDir, QSize


def natural_sort_key(s):
    """Natural sorting for filenames"""
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', str(s))]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Edit My Dataset")
        self.resize(800, 600)

        # Configuração de caminhos
        self.script_dir = Path(__file__).parent
        self.icons_dir = self.script_dir / "icons"

        # Data structures
        self.Map = OrderedDict()
        self.LabelDict = {}
        self.validLabels = set()
        self.ButtonPtr = []
        self.Directory = QDir()
        self.CurrentImg = 0
        self.TotalImg = 0
        self.scene = None
        self.TypeIconSize = 48
        self.lineEdit_Type = None

        self.strFilename = "filepath"
        self.strLabel = "label"
        self.strSeparator = ","

        self.setup_ui()
        self.load_toolbar_icons()
        self.load_init_data()

    def setup_ui(self):
        """Cria toda a interface manualmente"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(10)

        # ==================== TOP TOOLBAR ====================
        top_layout = QHBoxLayout()
        top_layout.setSpacing(6)

        self.toolButton_Save = QToolButton()
        self.toolButton_Save.setText("Save")
        self.toolButton_Save.setEnabled(False)
        self.toolButton_Save.setIconSize(QSize(64, 64))
        self.toolButton_Save.clicked.connect(self.on_toolButton_Save_clicked)

        self.toolButton_Previous = QToolButton()
        self.toolButton_Previous.setText("Previous")
        self.toolButton_Previous.setEnabled(False)
        self.toolButton_Previous.setIconSize(QSize(64, 64))
        self.toolButton_Previous.setShortcut(QKeySequence("Left"))
        self.toolButton_Previous.clicked.connect(self.on_toolButton_Previous_clicked)

        self.toolButton_Next = QToolButton()
        self.toolButton_Next.setText("Next")
        self.toolButton_Next.setEnabled(False)
        self.toolButton_Next.setIconSize(QSize(64, 64))
        self.toolButton_Next.setShortcut(QKeySequence("Right"))
        self.toolButton_Next.clicked.connect(self.on_toolButton_Next_clicked)

        self.toolButton_Exit = QToolButton()
        self.toolButton_Exit.setText("Exit")
        self.toolButton_Exit.setIconSize(QSize(64, 64))
        self.toolButton_Exit.clicked.connect(self.close)

        top_layout.addWidget(self.toolButton_Save)
        top_layout.addWidget(self.toolButton_Previous)
        top_layout.addWidget(self.toolButton_Next)
        top_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        top_layout.addWidget(self.toolButton_Exit)

        main_layout.addLayout(top_layout)

        # ==================== FORM LAYOUT ====================
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setSpacing(8)

        self.pushButton_Directory = QPushButton("Root directory:")
        self.pushButton_Directory.clicked.connect(self.on_pushButton_Directory_clicked)

        self.lineEdit_Directory = QLineEdit()
        self.lineEdit_Directory.setMinimumHeight(38)

        h_dir = QHBoxLayout()
        h_dir.addWidget(self.lineEdit_Directory)
        form_layout.addRow(self.pushButton_Directory, h_dir)

        self.pushButton_Csv = QPushButton("Input csv file:")
        self.pushButton_Csv.clicked.connect(self.on_pushButton_Csv_clicked)

        self.lineEdit_Csv = QLineEdit()
        self.lineEdit_Csv.setMinimumHeight(38)

        form_layout.addRow(self.pushButton_Csv, self.lineEdit_Csv)

        self.checkBox_hasHeader = QCheckBox("Csv has header")
        self.checkBox_hasHeader.setChecked(True)
        form_layout.addRow(self.checkBox_hasHeader)

        main_layout.addLayout(form_layout)

        # ==================== START BUTTON ====================
        self.pushButton_start = QPushButton("Read data and start")
        #self.pushButton_start.setFont(QFont("", 15))
        self.pushButton_start.clicked.connect(self.on_pushButton_start_clicked)
        main_layout.addWidget(self.pushButton_start)

        # ==================== IMAGE + LABEL BUTTONS ====================
        image_layout = QHBoxLayout()
        image_layout.setSpacing(10)

        self.graphicsView = QGraphicsView()
        self.graphicsView.setMinimumHeight(300)
        image_layout.addWidget(self.graphicsView, 3)

        self.verticalLayout_buttons = QVBoxLayout()
        image_layout.addLayout(self.verticalLayout_buttons, 1)

        main_layout.addLayout(image_layout, 1)

        # ==================== BOTTOM INFO ====================
        bottom_grid = QGridLayout()
        bottom_grid.setSpacing(8)

        label_filename = QLabel("Filename:")
        self.lineEdit_filename = QLineEdit()
        self.lineEdit_filename.setReadOnly(True)

        label_id = QLabel("ID of image:")
        self.spinBox_ID = QSpinBox()
        self.spinBox_ID.editingFinished.connect(self.on_spinBox_ID_editingFinished)

        label_type = QLabel("Type:")
        self.lineEdit_Type = QLineEdit()
        self.lineEdit_Type.setReadOnly(True)
        self.lineEdit_Type.setMaximumWidth(250)

        bottom_grid.addWidget(label_type, 0, 0, 2, 1)
        bottom_grid.addWidget(self.lineEdit_Type, 0, 1, 2, 1)
        bottom_grid.addWidget(label_filename, 0, 2)
        bottom_grid.addWidget(self.lineEdit_filename, 0, 3)
        bottom_grid.addWidget(label_id, 1, 2)
        bottom_grid.addWidget(self.spinBox_ID, 1, 3)

        main_layout.addLayout(bottom_grid)

        # ==================== PROGRESS BAR ====================
        self.progressBar = QProgressBar()
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(100)
        self.progressBar.setValue(0)
        main_layout.addWidget(self.progressBar)

        # ==================== MENU ====================
        menubar = QMenuBar()
        self.setMenuBar(menubar)
        menu_help = QMenu("Help", self)
        action_about = QAction("About", self)
        action_about.triggered.connect(self.on_actionAbout_triggered)
        menu_help.addAction(action_about)
        menubar.addMenu(menu_help)

    def load_toolbar_icons(self):
        """Carrega ícones da barra de ferramentas"""
        icon_map = {
            self.toolButton_Save: "document-save-all.png",
            self.toolButton_Previous: "go-previous.png",
            self.toolButton_Next: "go-next.png",
            self.toolButton_Exit: "exit.png",
            self.pushButton_Directory: "default-folder-saved-search.png",
            self.pushButton_Csv: "notebook.png",
            self.pushButton_start: "checkbox.png",
        }

        #icon_size = QSize(48, 48)

        for widget, icon_file in icon_map.items():
            icon_full_path = self.icons_dir / icon_file
            if icon_full_path.exists():
                widget.setIcon(QIcon(str(icon_full_path)))
                #widget.setIconSize(icon_size)
            else:
                print(f"⚠️ Ícone não encontrado: {icon_file}")

        # Ícone da janela
        app_icon = self.icons_dir / "edit-my-dataset.png"
        if app_icon.exists():
            self.setWindowIcon(QIcon(str(app_icon)))

    # ==================== RESTO DO CÓDIGO (igual ao anterior) ====================

    def load_init_data(self):
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

                if image_path and not os.path.isabs(image_path):
                    image_path = str(home / image_path)

                button = QPushButton(label, self)
                button.setEnabled(False)

                if image_path and os.path.exists(image_path):
                    pixmap = QPixmap(image_path)
                    button.setIcon(QIcon(pixmap))
                    if width > 0:
                        button.setIconSize(pixmap.rect().size().scaled(width, 999, Qt.KeepAspectRatio))

                if shortcut:
                    button.setShortcut(QKeySequence(shortcut))

                button.clicked.connect(lambda _, lbl=label: self.assign_label(lbl))

                self.verticalLayout_buttons.addWidget(button)
                self.ButtonPtr.append(button)

                self.LabelDict[label] = {
                    "button_image": image_path,
                    "button_image_width": width
                }

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load configuration:\n{e}")

    def create_default_file(self, filepath):
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
        if not self.Map:
            return
        filename = list(self.Map.keys())[self.CurrentImg]
        self.Map[filename] = label
        self.statusBar().showMessage(f"Last image labeled: {label}", 4000)
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
        self.Map = self.read_csv_file(  csv_file,
                                        filepath_column=self.strFilename, 
                                        label_column=self.strLabel, 
                                        separator=self.strSeparator,
                                        has_header=self.checkBox_hasHeader.isChecked())

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

        invalid = [f"{fn} → {lbl}" for fn, lbl in self.Map.items()
                   if lbl.strip() and lbl.strip() not in self.validLabels]

        if invalid:
            QMessageBox.warning(self, "Invalid Labels",
                                "Some labels are not valid:\n\n" + "\n".join(invalid[:15]))

        for btn in self.ButtonPtr:
            btn.setEnabled(True)
        self.toolButton_Previous.setEnabled(True)
        self.toolButton_Next.setEnabled(True)
        self.toolButton_Save.setEnabled(True)

        QMessageBox.information(self, "Ready", f"Loaded {self.TotalImg} images.")
        self.change_current_image()
        self.pushButton_start.setEnabled(True)

    def read_csv_file(self, csv_path, 
                      filepath_column="filepath", 
                      label_column="label", 
                      separator=",",
                      has_header=True):
        """
        Lê um CSV e retorna OrderedDict[filename -> label]
        """
        mapping = OrderedDict()
        
        if not os.path.exists(csv_path):
            QMessageBox.warning(self, "Error", f"CSV file not found:\n{csv_path}")
            return mapping

        try:
            import pandas as pd

            # Lê o CSV com pandas
            df = pd.read_csv(csv_path, 
                             sep=separator, 
                             header=0 if has_header else None,
                             dtype=str,           # força tudo como string
                             keep_default_na=False)

            # Normaliza nomes das colunas (remove espaços extras)
            df.columns = [col.strip() for col in df.columns]

            # Verifica se as colunas existem
            if filepath_column not in df.columns:
                QMessageBox.warning(self, "Warning", 
                                    f"Column '{filepath_column}' not found in CSV.\n"
                                    f"Available columns: {list(df.columns)}")
                return mapping

            if label_column not in df.columns:
                # Se não existir coluna de label, cria com valores vazios
                df[label_column] = ""

            # Preenche o OrderedDict
            for _, row in df.iterrows():
                filename = str(row[filepath_column]).strip()
                label = str(row[label_column]).strip() if pd.notna(row[label_column]) else ""
                if filename:  # ignora linhas com filename vazio
                    mapping[filename] = label

        except ImportError:
            QMessageBox.critical(self, "Error", "Pandas is not installed.\nRun: pip install pandas")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to read CSV:\n{str(e)}")

        return mapping

    def change_current_image(self):
        if not self.Map:
            return

        filename = list(self.Map.keys())[self.CurrentImg]
        label = self.Map[filename]
        
        print("")
        print("filename",filename)
        print("label",label)

        full_path = self.Directory.filePath(filename)
        self.statusBar().showMessage(f"Image: {full_path}", 3000)

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

        self.lineEdit_filename.setText(filename)
        self.spinBox_ID.setValue(self.CurrentImg)
        self.lineEdit_Type.setText(label)
        self.progressBar.setValue(self.CurrentImg)

        if label and label in self.LabelDict:
            icon_path = self.LabelDict[label]["button_image"]
            if icon_path and os.path.exists(icon_path):
                pix = QPixmap(icon_path).scaled(
                    self.TypeIconSize, self.TypeIconSize, Qt.KeepAspectRatio
                )
                self.lineEdit_Type.setPixmap(pix)


    def on_actionAbout_triggered(self):
        QMessageBox.about(self, "About Edit My Dataset",
                          "Program for editing / viewing tagged datasets.\n\n"
                          "Converted to pure Python + PyQt5.")

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
