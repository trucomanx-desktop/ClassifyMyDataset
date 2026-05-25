#!/usr/bin/python3

import os
import sys
import signal
import subprocess

import re
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QMessageBox, QProgressBar,
    QGroupBox, QRadioButton, QButtonGroup, QSizePolicy, QAction
)
from PyQt5.QtCore import Qt, QDir, QDirIterator
from PyQt5.QtGui import QFont, QIcon

import classify_my_dataset.about as about
import classify_my_dataset.modules.configure as configure 

from classify_my_dataset.modules.resources import resource_path
from classify_my_dataset.modules.wabout    import show_about_window

from classify_my_dataset.desktop import create_desktop_file
from classify_my_dataset.desktop import create_desktop_directory
from classify_my_dataset.desktop import create_desktop_menu

# ---------- Path to config file ----------
CONFIG_PATH = os.path.join( os.path.expanduser("~"),
                            ".config", 
                            about.__package__, 
                            f"config_{about.__program_prepare__}.json" )

DEFAULT_CONTENT={   
    "toolbar_configure": "Configure",
    "toolbar_configure_tooltip": "Open the configure Json file of program GUI",
    "toolbar_about": "About",
    "toolbar_about_tooltip": "About the program",
    "toolbar_coffee": "Coffee",
    "toolbar_coffee_tooltip": "Buy me a coffee (TrucomanX)",
    "window_width": 800,
    "window_height": 400,
    "group_title_dir": "1. Root Directory (Recursive)",
    "button_select_dir": "Select Root Directory",
    "group_title_filter": "2. File Filter",
    "line_edit_filter": "*.png *.jpg *.jpeg *.bmp",
    "label_filter": "Extensions (space separated):",
    "group_title_csv": "3. Output CSV File",
    "button_output_csv": "Select / Create CSV",
    "button_placeholder_csv": "/path/to/my_dataset.csv",
    "group_title_cols": "4. Column Names",
    "col_title_filepath": "filepath",
    "col_title_label": "label",
    "label_filepath": "Filepath Column:",
    "label_label": "Label Column:",
    "group_title_strategy": "5. Default Label Strategy",
    "strategy_none": "None (empty label)",
    "strategy_first": "First folder name",
    "strategy_last": "Last folder name",
    "generate_button": "Generate CSV",
    "exit_button": "Finish and Return",
    "select_root_directory": "Select Root Directory",
    "save_csv_file": "Save CSV File",
    "csv_file_filter": "CSV Files (*.csv)",
    "error": "Error",
    "error_select_directory": "Please select a valid root directory!",
    "error_output_file": "Please specify output CSV file!",
    "warning": "Warning",
    "warning_no_images": "No images found with the specified filters!",
    "success": "Success",
    "error_failed_generate": "Failed to generate CSV:",
    "success_message": "CSV generated successfully!",
    "success_total_images": "Total images:",
    "success_label_strategy": "Label strategy:",
    "success_file": "File:",
    "exit": "Exit"
}

configure.verify_default_config(CONFIG_PATH,default_content=DEFAULT_CONTENT)

CONFIG=configure.load_config(CONFIG_PATH)

# ---------------------------------------


class CSVGeneratorWindow(QMainWindow):
    def __init__(self, default_dir: str = ""):
        super().__init__()
        
        self.setWindowTitle(about.__program_prepare__)
        self.resize(CONFIG["window_width"], CONFIG["window_height"])
        
        ## Icon
        # Get base directory for icons
        self.icon_path = resource_path("icons", "prepare-classification-dataset.svg")
        self.setWindowIcon(QIcon(self.icon_path)) 
        
        self.generated_csv_path = None
        self.default_dir = default_dir
        self._create_toolbar()
        self.setup_ui()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        font_big = self.font()           # pega a fonte padrão da janela
        #font_big.setPointSize(11)

        font_title = self.font()
        #font_title.setPointSize(11)
        
        font_bold = self.font()
        font_bold.setBold(True)

        # ==================== ROOT DIRECTORY ====================
        group_dir = QGroupBox(CONFIG["group_title_dir"])
        form1 = QFormLayout()
        form1.setLabelAlignment(Qt.AlignRight)

        self.btn_dir = QPushButton(CONFIG["button_select_dir"])
        self.btn_dir.setIcon(QIcon(resource_path("icons", "default-folder-saved-search.svg")))
        self.btn_dir.clicked.connect(self.select_root_dir)
        
        self.line_dir = QLineEdit()
        self.line_dir.setFont(font_big)
        if self.default_dir:
            self.line_dir.setText(self.default_dir)

        h_dir = QHBoxLayout()
        h_dir.addWidget(self.line_dir)
        form1.addRow(self.btn_dir, h_dir)
        group_dir.setLayout(form1)
        layout.addWidget(group_dir)

        # ==================== FILE FILTER ====================
        group_filter = QGroupBox(CONFIG["group_title_filter"])
        form2 = QFormLayout()
        self.line_filter = QLineEdit(CONFIG["line_edit_filter"])
        self.line_filter.setFont(font_big)
        form2.addRow(CONFIG["label_filter"], self.line_filter)
        group_filter.setLayout(form2)
        layout.addWidget(group_filter)

        # ==================== OUTPUT CSV ====================
        group_out = QGroupBox(CONFIG["group_title_csv"])
        form3 = QFormLayout()
        self.btn_output = QPushButton(CONFIG["button_output_csv"] )
        self.btn_output.setIcon(QIcon(resource_path("icons", "notebook.svg")))
        self.btn_output.clicked.connect(self.select_output_csv)
        self.line_output = QLineEdit()
        self.line_output.setFont(font_big)
        self.line_output.setPlaceholderText(CONFIG["button_placeholder_csv"])

        h_out = QHBoxLayout()
        h_out.addWidget(self.line_output)
        form3.addRow(self.btn_output, h_out)
        group_out.setLayout(form3)
        layout.addWidget(group_out)

        # ==================== COLUMN NAMES ====================
        group_cols = QGroupBox(CONFIG["group_title_cols"])
        form4 = QFormLayout()
        self.line_col_filepath = QLineEdit(CONFIG["col_title_filepath"])
        self.line_col_label = QLineEdit(CONFIG["col_title_label"])
        form4.addRow(CONFIG["label_filepath"], self.line_col_filepath)
        form4.addRow(CONFIG["label_label"], self.line_col_label)
        group_cols.setLayout(form4)
        layout.addWidget(group_cols)

        # ==================== LABEL STRATEGY ====================
        group_label = QGroupBox(CONFIG["group_title_strategy"])
        label_layout = QVBoxLayout()

        self.radio_group = QButtonGroup(self)  # ← Importante!

        self.radio_none = QRadioButton(CONFIG["strategy_none"])
        self.radio_first = QRadioButton(CONFIG["strategy_first"])
        self.radio_last = QRadioButton(CONFIG["strategy_last"])

        self.radio_none.setChecked(True)

        self.radio_group.addButton(self.radio_none)
        self.radio_group.addButton(self.radio_first)
        self.radio_group.addButton(self.radio_last)

        label_layout.addWidget(self.radio_none)
        label_layout.addWidget(self.radio_first)
        label_layout.addWidget(self.radio_last)
        group_label.setLayout(label_layout)
        layout.addWidget(group_label)

        # ==================== PROGRESS ====================
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # ==================== BUTTONS ====================
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)

        self.btn_generate = QPushButton(CONFIG["generate_button"])
        self.btn_generate.setIcon(QIcon(resource_path("icons", "play-button.svg")))
        self.btn_generate.setFont(font_bold)
        self.btn_generate.clicked.connect(self.generate_csv)

        self.btn_finish = QPushButton(CONFIG["exit_button"])
        self.btn_finish.setIcon(QIcon(resource_path("icons", "exit.svg")))
        self.btn_finish.setFont(font_bold)
        self.btn_finish.clicked.connect(self.finish_and_return)

        btn_layout.addWidget(self.btn_generate)
        btn_layout.addWidget(self.btn_finish)
        layout.addLayout(btn_layout)

    # ==================== MÉTODOS ====================
    def _create_toolbar(self):
        self.toolbar = self.addToolBar("Main")
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)

        # Adicionar o espaçador
        self.toolbar_spacer = QWidget()
        self.toolbar_spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.toolbar.addWidget(self.toolbar_spacer)
        
        #
        self.configure_action = QAction(QIcon(resource_path("icons", "text-configure.svg")), 
                                        CONFIG["toolbar_configure"], 
                                        self)
        self.configure_action.setToolTip(CONFIG["toolbar_configure_tooltip"])
        self.configure_action.triggered.connect(self.open_configure_editor)
        self.toolbar.addAction(self.configure_action)
        
        #
        self.about_action = QAction(QIcon(resource_path("icons", "status_help.svg")), 
                                    CONFIG["toolbar_about"], 
                                    self)
        self.about_action.setToolTip(CONFIG["toolbar_about_tooltip"])
        self.about_action.triggered.connect(self.open_about)
        self.toolbar.addAction(self.about_action)
        
        # Coffee
        self.coffee_action = QAction(   QIcon(resource_path("icons", "emote-love.png")), 
                                        CONFIG["toolbar_coffee"], 
                                        self)
        self.coffee_action.setToolTip(CONFIG["toolbar_coffee_tooltip"])
        self.coffee_action.triggered.connect(self.on_coffee_action_click)
        self.toolbar.addAction(self.coffee_action)

        # Conectar ao sinal de mudança de orientação
        self.toolbar.orientationChanged.connect(self.on_update_spacer_policy)
        self.on_update_spacer_policy()

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
            "program_name": about.__program_prepare__,
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
        
        
    def select_root_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, 
                                                    CONFIG["select_root_directory"], 
                                                    self.line_dir.text())
        if dir_path:
            self.line_dir.setText(dir_path)

    def select_output_csv(self):
        file_path, _ = QFileDialog.getSaveFileName( self, 
                                                    CONFIG["save_csv_file"], 
                                                    "", 
                                                    CONFIG["csv_file_filter"])
        if file_path:
            if not file_path.endswith('.csv'):
                file_path += '.csv'
            self.line_output.setText(file_path)

    def get_label_strategy(self):
        if self.radio_first.isChecked():
            return "first"
        elif self.radio_last.isChecked():
            return "last"
        return "none"

    def generate_csv(self):
        root_dir = self.line_dir.text().strip()
        output_csv = self.line_output.text().strip()
        filter_text = self.line_filter.text().strip()
        strategy = self.get_label_strategy()

        if not root_dir or not os.path.exists(root_dir):
            QMessageBox.warning(self, CONFIG["error"], CONFIG["error_select_directory"])
            return
        if not output_csv:
            QMessageBox.warning(self, CONFIG["error"], CONFIG["error_output_file"])
            return

        self.btn_generate.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)  # Modo indeterminado enquanto busca
        QApplication.processEvents()

        try:
            filters = filter_text.split() if filter_text.strip() else ["*.png", "*.jpg", "*.jpeg", "*.bmp"]
            images = []
            it = QDirIterator(root_dir, filters, QDir.Files, QDirIterator.Subdirectories)

            while it.hasNext():
                file_path = it.next()
                rel_path = QDir(root_dir).relativeFilePath(file_path)
                images.append(rel_path)
                QApplication.processEvents()

            if not images:
                QMessageBox.warning(self, 
                                    CONFIG["warning"], 
                                    CONFIG["warning_no_images"])
                return

            images.sort(key=natural_sort_key)

            col_filepath = self.line_col_filepath.text().strip() or "filepath"
            col_label = self.line_col_label.text().strip() or "label"

            with open(output_csv, "w", encoding="utf-8", newline="") as f:
                f.write(f"{col_filepath},{col_label}\n")
                for rel_path in images:
                    label = ""
                    if strategy != "none":
                        parts = Path(rel_path).parts
                        if parts:
                            if strategy == "first":
                                label = parts[0]
                            elif strategy == "last":
                                label = parts[-2] if len(parts) > 1 else parts[0]
                    f.write(f"{rel_path},{label}\n")

            self.generated_csv_path = output_csv

            QMessageBox.information(self, 
                                    CONFIG["success"],
                                    CONFIG["success_message"]+"\n\n"+
                                    CONFIG["success_total_images"]+f" {len(images)}\n"+
                                    CONFIG["success_label_strategy"]+f" {strategy}\n"+
                                    CONFIG["success_file"]+f" {output_csv}")

        except Exception as e:
            QMessageBox.critical(self, CONFIG["error"], CONFIG["error_failed_generate"]+f"\n{str(e)}")
        finally:
            self.btn_generate.setEnabled(True)
            self.progress.setVisible(False)
            self.progress.setRange(0, 100)

    def finish_and_return(self):
        if self.generated_csv_path:
            self.close()
        else:
            reply = QMessageBox.question(self, CONFIG["exit"], 
                                         "No CSV was generated. Close anyway?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.close()

    def closeEvent(self, event):
        if self.generated_csv_path or QMessageBox.question(self, CONFIG["exit"], 
                                                             "Close without generating CSV?", 
                                                             QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()


def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', str(s))]


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
       
    icon_path = resource_path("icons", "prepare-classification-dataset.svg")
    '''
    extras="" # "MimeType=text/vnd.graphviz;"
    
    create_desktop_directory()    
    create_desktop_menu()
    create_desktop_file(os.path.join("~",".local","share","applications"), 
                        program_name=about.__program_name__,
                        extras=extras,
                        icon_path=icon_path)
    
    for n in range(len(sys.argv)):
        if sys.argv[n] == "--autostart":
            create_desktop_directory(overwrite = True)
            create_desktop_menu(overwrite = True)
            create_desktop_file(os.path.join("~",".config","autostart"), 
                                overwrite=True, 
                                program_name=about.__program_name__,
                                extras=extras,
                                icon_path=icon_path)
            return
        if sys.argv[n] == "--applications":
            create_desktop_directory(overwrite = True)
            create_desktop_menu(overwrite = True)
            create_desktop_file(os.path.join("~",".local","share","applications"), 
                                overwrite=True, 
                                program_name=about.__program_name__,
                                extras=extras,
                                icon_path=icon_path)
            return
    '''
    
    default_dir = sys.argv[1] if len(sys.argv) > 1 else ""

    
    app = QApplication(sys.argv)
    app.setApplicationName(about.__program_name__) 
    
    window = CSVGeneratorWindow(default_dir)
    window.show()
    sys.exit(app.exec_())
    
    #if window.generated_csv_path:
    #    print(f"CSV_GENERATED:{window.generated_csv_path}")
    
if __name__ == "__main__":
    main()
