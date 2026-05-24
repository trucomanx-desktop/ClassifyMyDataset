#!/usr/bin/python3
import sys
import os
import json
from pathlib import Path
from collections import OrderedDict
import re

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QLineEdit, QPushButton, QFileDialog, QMessageBox, QGraphicsScene,
    QGraphicsView, QListWidget, QListWidgetItem, QToolBar, QAction, QProgressBar,
    QFormLayout
)
from PyQt5.QtGui import QPixmap, QIcon, QFont
from PyQt5.QtCore import Qt, QDir, QSize


def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', str(s))]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Classify My Dataset")
        self.resize(1250, 720)

        # Data
        self.Map = OrderedDict() # filename -> label
        self.validLabels = set()
        self.ButtonPtr = []
        self.Directory = QDir()
        self.CurrentImg = None
        self.CurrentList = None
        self.scene = None

        self.setup_ui()
        self.load_icons()

    def setup_ui(self):
        # ==================== TOOLBAR ====================
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(48, 48))
        self.addToolBar(toolbar)

        self.action_save = QAction("Save", self)
        self.action_save.setShortcut("Ctrl+S")
        self.action_save.triggered.connect(self.save_csv)
        toolbar.addAction(self.action_save)

        toolbar.addSeparator()

        self.action_exit = QAction("Exit", self)
        self.action_exit.triggered.connect(self.close)
        toolbar.addAction(self.action_exit)

        # ==================== MAIN WIDGET ====================
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # === CONFIG SECTION (AGORA EM VERTICAL) ===
        config_group = QFormLayout()
        config_group.setLabelAlignment(Qt.AlignRight)
        config_group.setSpacing(12)

        # Root Directory
        self.line_dir = QLineEdit()
        btn_dir = QPushButton("...")
        btn_dir.setMaximumWidth(50)
        btn_dir.clicked.connect(self.select_root_dir)
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(self.line_dir, 1)
        dir_layout.addWidget(btn_dir)
        config_group.addRow("Root Directory:", dir_layout)

        # Input CSV
        self.line_csv = QLineEdit()
        btn_csv = QPushButton("...")
        btn_csv.setMaximumWidth(50)
        btn_csv.clicked.connect(self.select_csv)
        csv_layout = QHBoxLayout()
        csv_layout.addWidget(self.line_csv, 1)
        csv_layout.addWidget(btn_csv)
        config_group.addRow("Input CSV:", csv_layout)

        # Config JSON
        self.line_json = QLineEdit()
        btn_json = QPushButton("...")
        btn_json.setMaximumWidth(50)
        btn_json.clicked.connect(self.select_json)
        json_layout = QHBoxLayout()
        json_layout.addWidget(self.line_json, 1)
        json_layout.addWidget(btn_json)
        config_group.addRow("Config JSON:", json_layout)

        main_layout.addLayout(config_group)

        # Start Button
        self.btn_start = QPushButton("Load Dataset and Start")
        self.btn_start.clicked.connect(self.start_classification)
        main_layout.addWidget(self.btn_start)

        # ==================== MAIN AREA ====================
        content_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(content_splitter, 1)

        # LEFT: Two ListWidgets
        left_panel = QVBoxLayout()
        left_widget = QWidget()
        left_widget.setLayout(left_panel)

        self.list_unlabeled = QListWidget()
        self.list_labeled = QListWidget()

        lbl_un = QLabel("Without Label")
        lbl_un.setAlignment(Qt.AlignCenter)
        lbl_la = QLabel("With Label")
        lbl_la.setAlignment(Qt.AlignCenter)

        left_panel.addWidget(lbl_un)
        left_panel.addWidget(self.list_unlabeled, 1)
        left_panel.addWidget(lbl_la)
        left_panel.addWidget(self.list_labeled, 1)

        left_container = QWidget()
        left_container.setLayout(left_panel)
        content_splitter.addWidget(left_container)

        # CENTER: Image
        self.graphicsView = QGraphicsView()
        self.graphicsView.setMinimumWidth(500)
        content_splitter.addWidget(self.graphicsView)

        # RIGHT: Classification Buttons
        self.right_widget = QWidget()
        self.right_layout = QVBoxLayout(self.right_widget)
        self.right_layout.addStretch()
        content_splitter.addWidget(self.right_widget)

        content_splitter.setSizes([280, 650, 280])

        # Progress Bar
        self.progressBar = QProgressBar()
        self.progressBar.setFormat("Classified: %v / %m")
        main_layout.addWidget(self.progressBar)

        # Connections
        self.list_unlabeled.itemClicked.connect(
            lambda item: self.on_list_item_clicked(
                item,
                self.list_unlabeled
            )
        )

        self.list_labeled.itemClicked.connect(
            lambda item: self.on_list_item_clicked(
                item,
                self.list_labeled
            )
        )


    def load_icons(self):
        script_dir = Path(__file__).parent
        icons_dir = script_dir / "icons"
        icon_map = {
            self.action_save: "document-save-all.png",
            self.action_exit: "exit.png",
        }
        for action, icon_file in icon_map.items():
            path = icons_dir / icon_file
            if path.exists():
                action.setIcon(QIcon(str(path)))

    # ====================== SELECTORS ======================
    def select_root_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Select Root Directory")
        if path:
            self.line_dir.setText(path)

    def select_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select CSV File", "", "CSV (*.csv)")
        if path:
            self.line_csv.setText(path)

    def select_json(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Config JSON", "", "JSON (*.json)")
        if path:
            self.line_json.setText(path)

    # ====================== START ======================
    def start_classification(self):
        csv_path = self.line_csv.text().strip()
        json_path = self.line_json.text().strip()
        root_dir = self.line_dir.text().strip()

        if not csv_path or not os.path.exists(csv_path):
            QMessageBox.warning(self, "Error", "Please select a valid CSV file!")
            return
        if not json_path or not os.path.exists(json_path):
            QMessageBox.warning(self, "Error", "Please select a valid Config JSON file!")
            return
        if not root_dir or not os.path.exists(root_dir):
            QMessageBox.warning(self, "Error", "Please select Root Directory!")
            return

        self.Directory = QDir(root_dir)
        self.load_config(json_path)
        self.load_csv(csv_path)
        self.populate_lists()
        self.progressBar.setMaximum(len(self.Map))
        self.progressBar.setValue(sum(1 for v in self.Map.values() if v.strip()))

        if self.Map:
            self.show_first_image()
    def load_config(self, json_path):
        self.validLabels.clear()
        for btn in self.ButtonPtr:
            btn.setParent(None)
        self.ButtonPtr.clear()

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                buttons = json.load(f)

            for btn_data in buttons:
                label = btn_data.get("button_label", "").strip()
                if not label:
                    continue
                self.validLabels.add(label)

                button = QPushButton(label, self)
                #button.setMinimumHeight(60)
                button.clicked.connect(lambda _, lbl=label: self.assign_label(lbl))
                self.right_layout.addWidget(button)
                self.ButtonPtr.append(button)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load JSON config:\n{e}")
    def load_csv(self, csv_path):
        self.Map.clear()
        try:
            import pandas as pd
            df = pd.read_csv(csv_path, sep=",", dtype=str, keep_default_na=False)
            df.columns = [col.strip() for col in df.columns]
            filepath_col = df.columns[0]
            label_col = df.columns[1] if len(df.columns) > 1 else "label"
            for _, row in df.iterrows():
                fn = str(row[filepath_col]).strip()
                lbl = str(row.get(label_col, "")).strip()
                if fn:
                    self.Map[fn] = lbl
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to read CSV:\n{e}")
    def populate_lists(self):
        self.list_unlabeled.clear()
        self.list_labeled.clear()
        for filename, label in self.Map.items():
            item = QListWidgetItem(filename)
            if label and label in self.validLabels:
                self.list_labeled.addItem(item)
            else:
                self.list_unlabeled.addItem(item)

    def on_list_item_clicked(self, item, source_list):
        if not item:
            return

        # Limpa seleção da outra lista
        if source_list == self.list_unlabeled:
            self.list_labeled.clearSelection()
        else:
            self.list_unlabeled.clearSelection()

        filename = item.text()

        self.CurrentImg = filename
        self.CurrentList = source_list

        self.show_image(filename)
    
    def show_image(self, filename):
        full_path = self.Directory.filePath(filename)
        self.statusBar().showMessage(f"Image: {filename}", 4000)
        if self.scene:
            self.scene.clear()
        else:
            self.scene = QGraphicsScene(self)
            self.graphicsView.setScene(self.scene)
        pixmap = QPixmap(full_path)
        if not pixmap.isNull():
            scaled = pixmap.scaledToHeight(self.graphicsView.height() - 20, Qt.SmoothTransformation)
            self.scene.addPixmap(scaled)

    def assign_label(self, label: str):
        if not self.CurrentImg or not self.CurrentList:
            return

        current_list = self.CurrentList
        current_row = current_list.currentRow()

        # Atualiza label
        self.Map[self.CurrentImg] = label

        # Verifica se estava na unlabeled
        came_from_unlabeled = (
            current_list == self.list_unlabeled
        )

        # Refresh listas
        self.populate_lists()

        # ==========================
        # CASO 1:
        # Item saiu da unlabeled
        # ==========================
        if came_from_unlabeled:

            # Mantém mesma posição visual
            if current_row < self.list_unlabeled.count():

                self.list_unlabeled.setCurrentRow(current_row)

                item = self.list_unlabeled.item(current_row)

                self.on_list_item_clicked(
                    item,
                    self.list_unlabeled
                )

            elif self.list_unlabeled.count() > 0:

                # Se era último item
                last = self.list_unlabeled.count() - 1

                self.list_unlabeled.setCurrentRow(last)

                item = self.list_unlabeled.item(last)

                self.on_list_item_clicked(
                    item,
                    self.list_unlabeled
                )

            elif self.list_labeled.count() > 0:

                # Sem unlabeled restantes
                self.list_labeled.setCurrentRow(0)

                item = self.list_labeled.item(0)

                self.on_list_item_clicked(
                    item,
                    self.list_labeled
                )

        # ==========================
        # CASO 2:
        # Veio da labeled
        # ==========================
        else:

            next_row = current_row + 1

            if next_row < self.list_labeled.count():

                self.list_labeled.setCurrentRow(next_row)

                item = self.list_labeled.item(next_row)

                self.on_list_item_clicked(
                    item,
                    self.list_labeled
                )

            elif self.list_labeled.count() > 0:

                # Continua no último
                last = self.list_labeled.count() - 1

                self.list_labeled.setCurrentRow(last)

                item = self.list_labeled.item(last)

                self.on_list_item_clicked(
                    item,
                    self.list_labeled
                )

        # Atualiza progresso
        classified_count = sum(
            1 for v in self.Map.values()
            if v.strip()
        )

        self.progressBar.setValue(classified_count)


    def show_first_image(self):
        """Mostra a primeira imagem disponível"""

        if self.list_unlabeled.count() > 0:

            self.list_unlabeled.setCurrentRow(0)

            item = self.list_unlabeled.item(0)

            self.on_list_item_clicked(
                item,
                self.list_unlabeled
            )

        elif self.list_labeled.count() > 0:

            self.list_labeled.setCurrentRow(0)

            item = self.list_labeled.item(0)

            self.on_list_item_clicked(
                item,
                self.list_labeled
            )

    def save_csv(self):
        if not self.Map:
            QMessageBox.warning(self, "Warning", "No data loaded!")
            return
        csv_path = self.line_csv.text().strip()
        if not csv_path:
            csv_path, _ = QFileDialog.getSaveFileName(self, "Save CSV", "", "CSV (*.csv)")
        if csv_path:
            try:
                with open(csv_path, "w", encoding="utf-8", newline="") as f:
                    f.write("filepath,label\n")
                    for fn, lbl in self.Map.items():
                        f.write(f"{fn},{lbl}\n")
                QMessageBox.information(self, "Success", "CSV saved successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def closeEvent(self, event):
        reply = QMessageBox.question(self, "Exit", "Close the program?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
if __name__ == "__main__":
    main()
