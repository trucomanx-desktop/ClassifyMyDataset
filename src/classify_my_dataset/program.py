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
    QFrame
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
        self.resize(1200, 700)

        # Data
        self.Map = OrderedDict()           # filename -> label
        self.validLabels = set()
        self.ButtonPtr = []
        self.Directory = QDir()
        self.CurrentImg = None
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
        main_layout.setSpacing(8)

        # === CONFIG SECTION ===
        config_layout = QHBoxLayout()
        config_layout.setSpacing(15)

        # Root Directory
        lbl_dir = QLabel("Root Directory:")
        self.line_dir = QLineEdit()
        btn_dir = QPushButton("...")
        btn_dir.setMaximumWidth(40)
        btn_dir.clicked.connect(self.select_root_dir)

        # Input CSV
        lbl_csv = QLabel("Input CSV:")
        self.line_csv = QLineEdit()
        btn_csv = QPushButton("...")
        btn_csv.setMaximumWidth(40)
        btn_csv.clicked.connect(self.select_csv)

        # Config JSON
        lbl_json = QLabel("Config JSON:")
        self.line_json = QLineEdit()
        btn_json = QPushButton("...")
        btn_json.setMaximumWidth(40)
        btn_json.clicked.connect(self.select_json)

        config_layout.addWidget(lbl_dir)
        config_layout.addWidget(self.line_dir, 2)
        config_layout.addWidget(btn_dir)

        config_layout.addWidget(lbl_csv)
        config_layout.addWidget(self.line_csv, 2)
        config_layout.addWidget(btn_csv)

        config_layout.addWidget(lbl_json)
        config_layout.addWidget(self.line_json, 2)
        config_layout.addWidget(btn_json)

        main_layout.addLayout(config_layout)

        # Start Button
        self.btn_start = QPushButton("Load Dataset and Start")
        self.btn_start.setFont(QFont("", 12, QFont.Bold))
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
        self.graphicsView.setMinimumWidth(400)
        content_splitter.addWidget(self.graphicsView)

        # RIGHT: Classification Buttons
        self.right_widget = QWidget()
        self.right_layout = QVBoxLayout(self.right_widget)
        self.right_layout.addStretch()
        content_splitter.addWidget(self.right_widget)

        content_splitter.setSizes([250, 600, 250])

        # Progress Bar
        self.progressBar = QProgressBar()
        self.progressBar.setFormat("Classified: %v / %m")
        main_layout.addWidget(self.progressBar)

        # Connections
        self.list_unlabeled.itemClicked.connect(self.on_list_item_clicked)
        self.list_labeled.itemClicked.connect(self.on_list_item_clicked)

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
        self.progressBar.setValue(sum(1 for v in self.Map.values() if v))

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
                button.setMinimumHeight(60)
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

    def show_first_image(self):
        if self.list_unlabeled.count() > 0:
            self.list_unlabeled.setCurrentRow(0)
            self.on_list_item_clicked(self.list_unlabeled.item(0))
        elif self.list_labeled.count() > 0:
            self.list_labeled.setCurrentRow(0)
            self.on_list_item_clicked(self.list_labeled.item(0))

    def on_list_item_clicked(self, item):
        if not item:
            return
        filename = item.text()
        self.CurrentImg = filename
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
        if not self.CurrentImg:
            return

        # Salva o label
        self.Map[self.CurrentImg] = label

        # Refresh das listas
        self.populate_lists()

        # Avança para o próximo da MESMA lista de onde veio
        self.auto_advance_smart()

        # Atualiza progresso
        classified_count = sum(1 for v in self.Map.values() if v.strip())
        self.progressBar.setValue(classified_count)

    def auto_advance_smart(self):
        """Avança para o próximo item da mesma lista de onde veio a imagem atual"""
        if not self.CurrentImg:
            return

        # Verifica em qual lista está a imagem atual
        current_item = None
        list_widget = None

        # Procura na lista de labeled
        for i in range(self.list_labeled.count()):
            if self.list_labeled.item(i).text() == self.CurrentImg:
                list_widget = self.list_labeled
                current_item = i
                break

        # Se não encontrou, procura na unlabeled
        if list_widget is None:
            for i in range(self.list_unlabeled.count()):
                if self.list_unlabeled.item(i).text() == self.CurrentImg:
                    list_widget = self.list_unlabeled
                    current_item = i
                    break

        if list_widget is None:
            # Fallback
            self.show_first_image()
            return

        # Avança para o próximo item da mesma lista
        next_index = current_item + 1

        if next_index < list_widget.count():
            # Ainda tem itens na mesma lista
            list_widget.setCurrentRow(next_index)
            self.on_list_item_clicked(list_widget.item(next_index))
        else:
            # Fim da lista atual → vai para a outra lista (se tiver itens)
            if list_widget == self.list_labeled and self.list_unlabeled.count() > 0:
                self.list_unlabeled.setCurrentRow(0)
                self.on_list_item_clicked(self.list_unlabeled.item(0))
            elif list_widget == self.list_unlabeled and self.list_labeled.count() > 0:
                self.list_labeled.setCurrentRow(0)
                self.on_list_item_clicked(self.list_labeled.item(0))
            else:
                # Não tem mais imagens
                self.CurrentImg = None
                self.statusBar().showMessage("All images processed!", 4000)

    def show_first_image(self):
        """Mostra a primeira imagem disponível (prioridade para unlabeled)"""
        if self.list_unlabeled.count() > 0:
            self.list_unlabeled.setCurrentRow(0)
            self.on_list_item_clicked(self.list_unlabeled.item(0))
        elif self.list_labeled.count() > 0:
            self.list_labeled.setCurrentRow(0)
            self.on_list_item_clicked(self.list_labeled.item(0))

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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
