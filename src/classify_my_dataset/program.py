#!/usr/bin/python3

import os
import sys
import json
import signal
import subprocess

from pathlib import Path
from collections import OrderedDict
import re

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QLineEdit, QPushButton, QFileDialog, QMessageBox, QGraphicsScene,
    QGraphicsView, QListWidget, QListWidgetItem, QToolBar, QAction, QProgressBar,
    QFormLayout, QSizePolicy
)
from PyQt5.QtGui import QPixmap, QIcon, QFont, QDesktopServices
from PyQt5.QtCore import Qt, QDir, QSize, QUrl

import classify_my_dataset.about as about
import classify_my_dataset.modules.configure as configure 
from classify_my_dataset.modules.resources import resource_path
from classify_my_dataset.program_prepare import CSVGeneratorWindow

from classify_my_dataset.modules.wabout    import show_about_window
from classify_my_dataset.desktop import create_desktop_file, create_desktop_directory, create_desktop_menu


# ---------- Path to config file ----------
CONFIG_PATH = os.path.join( os.path.expanduser("~"),
                            ".config", 
                            about.__package__, 
                            f"config_{about.__program_classify__}.json" )

DEFAULT_CONTENT={
    "toolbar_save": "Save",
    "toolbar_save_tooltip": "Save the CSV file with the current data",
    "toolbar_configure": "Configure",
    "toolbar_configure_tooltip": "Open the configure Json file of program GUI",
    "toolbar_about": "About",
    "toolbar_about_tooltip": "About the program",
    "toolbar_coffee": "Coffee",
    "toolbar_coffee_tooltip": "Buy me a coffee (TrucomanX)",
    "toolbar_exit": "Exit",
    "toolbar_exit_tooltip": "Exit of application",
    "window_width": 1024,
    "window_height": 800,
    "root_dir_lineedit_placeholder": "/path/of/root/directory/dataset/",
    "root_dir_lineedit_tooltip": "Root directory of dataset",
    "root_dir_button": "Select Root",
    "root_dir_button_tooltip": "Select root directory of dataset",
    "root_dir_label": "Root Directory:",
    "csv_lineedit_placeholder": "/path/of/working/filename.csv",
    "csv_lineedit_tooltip": "The CSV file with the file path of samples",
    "csv_button": "Select *.csv",
    "csv_button_tooltip": "Select the CSV file with the file path of samples",
    "csv_label": "Input CSV:",
    "json_lineedit_placeholder": "/path/of/working/filename.classify.json",
    "json_lineedit_tooltip": "The JSON config file with the dataset labels",
    "json_button": "Select *.classify.json",
    "json_button_tooltip": "Select the JSON config file with the dataset labels",
    "json_label": "Config JSON:",
    "start_button": "Start",
    "start_button_tooltip": "Load dataset and start the classification process",
}

configure.verify_default_config(CONFIG_PATH,default_content=DEFAULT_CONTENT)

CONFIG=configure.load_config(CONFIG_PATH)

# ---------------------------------------


def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', str(s))]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle(about.__program_classify__)
        self.resize(CONFIG["window_width"], CONFIG["window_height"])
        
        ## Icon
        # Get base directory for icons
        self.icon_path = resource_path("icons", "logo.svg")
        self.setWindowIcon(QIcon(self.icon_path)) 
        

        # Data
        self.Map = OrderedDict() # filename -> label
        self.validLabels = set()
        self.ButtonPtr = []
        self.Directory = QDir()
        self.CurrentImg = None
        self.CurrentList = None
        self.scene = None

        self._create_toolbar()
        self.setup_ui()

    def _create_toolbar(self):
        self.toolbar = self.addToolBar("Main")
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)

        # Save
        self.action_save = QAction( QIcon(resource_path("icons","download.svg")),
                                    CONFIG["toolbar_save"], 
                                    self)
        self.action_save.setShortcut("Ctrl+S")
        self.action_save.setToolTip(CONFIG["toolbar_save_tooltip"])
        self.action_save.triggered.connect(self.save_csv)
        self.toolbar.addAction(self.action_save)

        #
        self.action_prepare_csv = QAction(
            QIcon(resource_path(
                "icons",
                "prepare-classification-dataset.svg"
            )),
            "Prepare CSV",
            self
        )

        self.action_prepare_csv.setToolTip(
            "Open CSV generator"
        )

        self.action_prepare_csv.triggered.connect(
            self.open_prepare_csv_window
        )

        self.toolbar.addAction(
            self.action_prepare_csv
        )


        # Adicionar o espaçador
        self.toolbar_spacer = QWidget()
        self.toolbar_spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.toolbar.addWidget(self.toolbar_spacer)
        
        #
        self.configure_action = QAction(QIcon(resource_path("icons","text-configure.svg")), 
                                        CONFIG["toolbar_configure"], 
                                        self)
        self.configure_action.setToolTip(CONFIG["toolbar_configure_tooltip"])
        self.configure_action.triggered.connect(self.open_configure_editor)
        self.toolbar.addAction(self.configure_action)
        
        # About
        self.about_action = QAction(QIcon(resource_path("icons","status_help.svg")), 
                                    CONFIG["toolbar_about"], 
                                    self)
        self.about_action.setToolTip(CONFIG["toolbar_about_tooltip"])
        self.about_action.triggered.connect(self.open_about)
        self.toolbar.addAction(self.about_action)
        
        # Coffee
        self.coffee_action = QAction(   QIcon(resource_path("icons","emote-love.png")), 
                                        CONFIG["toolbar_coffee"], 
                                        self)
        self.coffee_action.setToolTip(CONFIG["toolbar_coffee_tooltip"])
        self.coffee_action.triggered.connect(self.on_coffee_action_click)
        self.toolbar.addAction(self.coffee_action)

        #
        self.action_exit = QAction( QIcon(resource_path("icons","exit.svg")),
                                    CONFIG["toolbar_exit"], 
                                    self)
        self.action_exit.setToolTip(CONFIG["toolbar_exit_tooltip"])
        self.action_exit.triggered.connect(self.close)
        self.toolbar.addAction(self.action_exit)


        # Conectar ao sinal de mudança de orientação
        self.toolbar.orientationChanged.connect(self.on_update_spacer_policy)
        self.on_update_spacer_policy()


    def setup_ui(self):

        # ==================== MAIN WIDGET ====================
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        #main_layout.setSpacing(10)
        #main_layout.setContentsMargins(10, 10, 10, 10)

        # === CONFIG SECTION (AGORA EM VERTICAL) ===
        config_group = QFormLayout()
        config_group.setLabelAlignment(Qt.AlignRight)
        #config_group.setSpacing(12)

        # Root Directory
        self.line_dir = QLineEdit()
        self.line_dir.setPlaceholderText(CONFIG["root_dir_lineedit_placeholder"])
        self.line_dir.setToolTip(CONFIG["root_dir_lineedit_tooltip"])
        btn_dir = QPushButton(CONFIG["root_dir_button"])
        btn_dir.setStyleSheet("""
            text-align: left;
            padding-left: 10px;
        """)
        btn_dir.setMinimumWidth(200)
        btn_dir.setIcon(QIcon(resource_path("icons","default-folder-saved-search.svg")))
        btn_dir.setToolTip(CONFIG["root_dir_button_tooltip"])
        btn_dir.clicked.connect(self.select_root_dir)
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(self.line_dir, 1)
        dir_layout.addWidget(btn_dir)
        config_group.addRow(CONFIG["root_dir_label"], dir_layout)
        
        # Input CSV
        self.line_csv = QLineEdit()
        self.line_csv.setPlaceholderText(CONFIG["csv_lineedit_placeholder"])
        self.line_csv.setToolTip(CONFIG["csv_lineedit_tooltip"])
        btn_csv = QPushButton(CONFIG["csv_button"])
        btn_csv.setStyleSheet("""
            text-align: left;
            padding-left: 10px;
        """)
        btn_csv.setMinimumWidth(200)
        btn_csv.setIcon(QIcon(resource_path("icons","notebook.svg")))
        btn_csv.setToolTip(CONFIG["csv_button_tooltip"])
        btn_csv.clicked.connect(self.select_csv)
        csv_layout = QHBoxLayout()
        csv_layout.addWidget(self.line_csv, 1)
        csv_layout.addWidget(btn_csv)
        config_group.addRow(CONFIG["csv_label"], csv_layout)

        # Config JSON
        self.line_json = QLineEdit()
        self.line_json.setPlaceholderText(CONFIG["json_lineedit_placeholder"])
        self.line_json.setToolTip(CONFIG["json_lineedit_tooltip"])
        btn_json = QPushButton(CONFIG["json_button"])
        btn_json.setStyleSheet("""
            text-align: left;
            padding-left: 10px;
        """)
        btn_json.setMinimumWidth(200)
        btn_json.setIcon(QIcon(resource_path("icons","notebook.svg")))
        btn_json.setToolTip(CONFIG["json_button_tooltip"])
        btn_json.clicked.connect(self.select_json)
        json_layout = QHBoxLayout()
        json_layout.addWidget(self.line_json, 1)
        json_layout.addWidget(btn_json)
        config_group.addRow(CONFIG["json_label"], json_layout)

        main_layout.addLayout(config_group)

        # Start Button
        self.btn_start = QPushButton(CONFIG["start_button"])
        self.btn_start.setIcon(QIcon(resource_path("icons","view-refresh.svg")))
        self.btn_start.setToolTip(CONFIG["start_button_tooltip"])
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

        content_splitter.setSizes([380, 650, 180])


        # ==================== CURRENT CATEGORY ====================

        category_layout = QHBoxLayout()

        self.lbl_current_category = QLabel("Current Category:")

        self.line_current_category = QLineEdit()
        self.line_current_category.setReadOnly(True)
        self.line_current_category.setStyleSheet("""
            QLineEdit {
                background-color: #f0f0f0;
                font-weight: bold;
                padding: 4px;
            }
        """)

        category_layout.addWidget(self.lbl_current_category)
        category_layout.addWidget(self.line_current_category, 1)

        main_layout.addLayout(category_layout)

        # ==================== PROGRESS BAR ====================

        self.progressBar = QProgressBar()
        self.progressBar.setFormat("Classified: %v / %m")
        main_layout.addWidget(self.progressBar)

        # =========================
        # CONNECTIONS
        # =========================

        self.list_unlabeled.currentItemChanged.connect(
            lambda current, previous:
            self.on_list_item_clicked(
                current,
                self.list_unlabeled
            )
        )

        self.list_labeled.currentItemChanged.connect(
            lambda current, previous:
            self.on_list_item_clicked(
                current,
                self.list_labeled
            )
        )

    def on_update_spacer_policy(self):
        """Atualiza a política do espaçador baseado na orientação da toolbar"""
        if self.toolbar.orientation() == Qt.Horizontal:
            # Horizontal: expande na largura
            self.toolbar_spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        else:
            # Vertical: expande na altura
            self.toolbar_spacer.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

    def _open_file_in_text_editor(self, filepath):
        if os.name == 'nt':  # Windows
            os.startfile(filepath)
        elif os.name == 'posix':  # Linux/macOS
            subprocess.run(['xdg-open', filepath])
    
    def open_url_usage_editor(self):
        QDesktopServices.openUrl(QUrl(CONFIG_GPT["usage"]))
        
    def open_configure_editor(self):
        self._open_file_in_text_editor(CONFIG_PATH)

    def open_about(self):
        data={
            "version": about.__version__,
            "package": about.__package__,
            "program_name": about.__program_classify__,
            "author": about.__author__,
            "email": about.__email__,
            "description": about.__description__,
            "url_source": about.__url_source__,
            "url_doc": about.__url_doc__,
            "url_funding": about.__url_funding__,
            "url_bugs": about.__url_bugs__
        }
        show_about_window(data,self.icon_path)

    def on_coffee_action_click(self):
        QDesktopServices.openUrl(QUrl("https://ko-fi.com/trucomanx"))

    # ====================== WINDOW ======================
    def open_prepare_csv_window(self):

        root_dir = self.line_dir.text().strip()

        self.prepare_window = CSVGeneratorWindow(
            default_dir=root_dir
        )

        self.prepare_window.show()
        
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
        path, _ = QFileDialog.getOpenFileName(self, "Select Config JSON", "", "JSON (*.classify.json)")
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

        # Remove botões antigos
        for btn in self.ButtonPtr:
            btn.deleteLater()

        self.ButtonPtr.clear()

        try:

            with open(json_path, "r", encoding="utf-8") as f:
                buttons = json.load(f)

            if not isinstance(buttons, list):
                raise Exception("JSON root must be a list")

            for btn_data in buttons:

                if not isinstance(btn_data, dict):
                    continue

                # =========================
                # REQUIRED
                # =========================

                label = str(
                    btn_data.get("button_label", "")
                ).strip()

                if not label:
                    continue

                self.validLabels.add(label)

                # =========================
                # CREATE BUTTON
                # =========================

                button = QPushButton(label, self)

                button.setMinimumHeight(48)

                # =========================
                # OPTIONAL SHORTCUT
                # =========================

                shortcut = str(
                    btn_data.get("short_cut", "")
                ).strip()

                if shortcut:
                    button.setShortcut(shortcut)
                    button.setToolTip(f"shortcut: {shortcut}")

                # =========================
                # OPTIONAL IMAGE
                # =========================

                image_path = str(
                    btn_data.get("button_image", "")
                ).strip()

                if image_path:

                    if os.path.exists(image_path):

                        icon = QIcon(image_path)

                        button.setIcon(icon)

                        # Optional width
                        image_width = btn_data.get(
                            "button_image_width",
                            32
                        )

                        try:
                            image_width = int(image_width)

                            if image_width <= 0:
                                image_width = 32

                        except:
                            image_width = 32

                        button.setIconSize(
                            QSize(
                                image_width,
                                image_width
                            )
                        )

                    else:

                        print(
                            f"[WARNING] Image not found: "
                            f"{image_path}"
                        )

                # =========================
                # STYLE
                # =========================

                button.setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        padding: 8px;
                        font-size: 14px;
                    }
                """)

                # =========================
                # CONNECT
                # =========================

                button.clicked.connect(
                    lambda _, lbl=label:
                    self.assign_label(lbl)
                )

                # =========================
                # ADD TO UI
                # =========================

                self.right_layout.addWidget(button)

                self.ButtonPtr.append(button)

        except Exception as e:

            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load JSON config:\n{e}"
            )
            
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

        # Atualiza categoria atual
        current_label = self.Map.get(filename, "").strip()

        if current_label:
            self.line_current_category.setText(current_label)
        else:
            self.line_current_category.setText("")

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
        
        self.line_current_category.setText(label)

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
    signal.signal(signal.SIGINT, signal.SIG_DFL)
       
    '''
    extras="" # "MimeType=text/vnd.graphviz;"
    
    create_desktop_directory()    
    create_desktop_menu()
    create_desktop_file(os.path.join("~",".local","share","applications"), 
                        program_name=about.__program_classify__,
                        extras=extras)
    
    for n in range(len(sys.argv)):
        if sys.argv[n] == "--autostart":
            create_desktop_directory(overwrite = True)
            create_desktop_menu(overwrite = True)
            create_desktop_file(os.path.join("~",".config","autostart"), 
                                overwrite=True, 
                                program_name=about.__program_classify__,
                                extras=extras)
            return
        if sys.argv[n] == "--applications":
            create_desktop_directory(overwrite = True)
            create_desktop_menu(overwrite = True)
            create_desktop_file(os.path.join("~",".local","share","applications"), 
                                overwrite=True, 
                                program_name=about.__program_classify__,
                                extras=extras)
            return
    '''
    
    app = QApplication(sys.argv)
    app.setApplicationName(about.__program_classify__) 
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
