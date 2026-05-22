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
    "window_height": 400
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
        self.icon_path = resource_path("icons", "logo.png")
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
        group_dir = QGroupBox("1. Root Directory (Recursive)")
        form1 = QFormLayout()
        form1.setLabelAlignment(Qt.AlignRight)

        self.btn_dir = QPushButton("Select Root Directory")
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
        group_filter = QGroupBox("2. File Filter")
        form2 = QFormLayout()
        self.line_filter = QLineEdit("*.png *.jpg *.jpeg *.bmp")
        self.line_filter.setFont(font_big)
        form2.addRow("Extensions (space separated):", self.line_filter)
        group_filter.setLayout(form2)
        layout.addWidget(group_filter)

        # ==================== OUTPUT CSV ====================
        group_out = QGroupBox("3. Output CSV File")
        form3 = QFormLayout()
        self.btn_output = QPushButton("Select / Create CSV")
        self.btn_output.clicked.connect(self.select_output_csv)
        self.line_output = QLineEdit()
        self.line_output.setFont(font_big)
        self.line_output.setPlaceholderText("/path/to/my_dataset.csv")

        h_out = QHBoxLayout()
        h_out.addWidget(self.line_output)
        form3.addRow(self.btn_output, h_out)
        group_out.setLayout(form3)
        layout.addWidget(group_out)

        # ==================== COLUMN NAMES ====================
        group_cols = QGroupBox("4. Column Names")
        form4 = QFormLayout()
        self.line_col_filepath = QLineEdit("filepath")
        self.line_col_label = QLineEdit("label")
        form4.addRow("Filepath Column:", self.line_col_filepath)
        form4.addRow("Label Column:", self.line_col_label)
        group_cols.setLayout(form4)
        layout.addWidget(group_cols)

        # ==================== LABEL STRATEGY ====================
        group_label = QGroupBox("5. Default Label Strategy")
        label_layout = QVBoxLayout()

        self.radio_group = QButtonGroup(self)  # ← Importante!

        self.radio_none = QRadioButton("None (empty label)")
        self.radio_first = QRadioButton("First folder name")
        self.radio_last = QRadioButton("Last folder name")

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

        self.btn_generate = QPushButton("Generate CSV")
        self.btn_generate.setFont(font_bold)
        self.btn_generate.clicked.connect(self.generate_csv)

        self.btn_finish = QPushButton("Finish and Return")
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
        self.configure_action = QAction(QIcon.fromTheme("document-properties"), 
                                        CONFIG["toolbar_configure"], 
                                        self)
        self.configure_action.setToolTip(CONFIG["toolbar_configure_tooltip"])
        self.configure_action.triggered.connect(self.open_configure_editor)
        self.toolbar.addAction(self.configure_action)
        
        #
        self.about_action = QAction(QIcon.fromTheme("help-about"), 
                                    CONFIG["toolbar_about"], 
                                    self)
        self.about_action.setToolTip(CONFIG["toolbar_about_tooltip"])
        self.about_action.triggered.connect(self.open_about)
        self.toolbar.addAction(self.about_action)
        
        # Coffee
        self.coffee_action = QAction(   QIcon.fromTheme("emblem-favorite"), 
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
        dir_path = QFileDialog.getExistingDirectory(self, "Select Root Directory", self.line_dir.text())
        if dir_path:
            self.line_dir.setText(dir_path)

    def select_output_csv(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save CSV File", "", "CSV Files (*.csv)")
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
            QMessageBox.warning(self, "Error", "Please select a valid root directory!")
            return
        if not output_csv:
            QMessageBox.warning(self, "Error", "Please specify output CSV file!")
            return

        self.btn_generate.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)  # Modo indeterminado enquanto busca
        QApplication.processEvents()

        try:
            filters = filter_text.split() if filter_text else ["*.png", "*.jpg", "*.jpeg", "*.bmp"]
            images = []
            it = QDirIterator(root_dir, filters, QDir.Files, QDirIterator.Subdirectories)

            while it.hasNext():
                file_path = it.next()
                rel_path = QDir(root_dir).relativeFilePath(file_path)
                images.append(rel_path)
                QApplication.processEvents()

            if not images:
                QMessageBox.warning(self, "Warning", "No images found with the specified filters!")
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

            QMessageBox.information(self, "Success",
                                  f"CSV generated successfully!\n\n"
                                  f"Total images: {len(images)}\n"
                                  f"Label strategy: {strategy}\n"
                                  f"File: {output_csv}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate CSV:\n{str(e)}")
        finally:
            self.btn_generate.setEnabled(True)
            self.progress.setVisible(False)
            self.progress.setRange(0, 100)

    def finish_and_return(self):
        if self.generated_csv_path:
            self.close()
        else:
            reply = QMessageBox.question(self, "Exit", 
                                         "No CSV was generated. Close anyway?",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.close()

    def closeEvent(self, event):
        if self.generated_csv_path or QMessageBox.question(self, "Exit", 
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
       
    '''
    extras="" # "MimeType=text/vnd.graphviz;"
    
    create_desktop_directory()    
    create_desktop_menu()
    create_desktop_file(os.path.join("~",".local","share","applications"), 
                        program_name=about.__program_name__,
                        extras=extras)
    
    for n in range(len(sys.argv)):
        if sys.argv[n] == "--autostart":
            create_desktop_directory(overwrite = True)
            create_desktop_menu(overwrite = True)
            create_desktop_file(os.path.join("~",".config","autostart"), 
                                overwrite=True, 
                                program_name=about.__program_name__,
                                extras=extras)
            return
        if sys.argv[n] == "--applications":
            create_desktop_directory(overwrite = True)
            create_desktop_menu(overwrite = True)
            create_desktop_file(os.path.join("~",".local","share","applications"), 
                                overwrite=True, 
                                program_name=about.__program_name__,
                                extras=extras)
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
