import json
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QScrollArea, QCheckBox, 
                             QFileDialog, QMessageBox, QGridLayout, QTextEdit, QFrame,QShortcut)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QKeySequence

class TranslationValidator(QMainWindow):
    check_translation_signal = pyqtSignal(int, int)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Translation Validator")
        self.resize(2100, 1500)  # Twice as wide, 1.5x as tall
        
        self.data = None
        self.current_index = 0
        self.filename = ""
        self.fuzzy_input_mode = False
        self.current_fuzzy_num = 0
        self.current_trans_num = 0
        
        self.init_ui()
        self.load_file()
        
    def init_ui(self):
        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        

        # Main sentence display
        self.main_sentence_label = QLabel("Main Sentence:")
        self.main_sentence_label.setStyleSheet("font-weight: bold; font-size: 32px;")
        self.main_layout.addWidget(self.main_sentence_label)
        
        self.main_sentence_text = QLineEdit()
        self.main_sentence_text.setReadOnly(True)
        self.main_sentence_text.setStyleSheet("font-size: 32px;")
        self.main_layout.addWidget(self.main_sentence_text)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        self.main_layout.addWidget(separator)
        
        # Fuzzy matches scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 20, 0)  # Right margin for scrollbar
        self.scroll_area.setWidget(self.scroll_content)
        self.main_layout.addWidget(self.scroll_area, 1)
        
        # Status label for input mode
        self.status_label = QLabel("Press a number to select fuzzy match")
        self.status_label.setStyleSheet("font-style: italic; color: #555;")
        self.main_layout.addWidget(self.status_label)
        

        self.reset_input_mode()


        # Button layout
        self.button_layout = QHBoxLayout()
        self.button_layout.setSpacing(20)
        
        self.back_btn = QPushButton("Back (B)")
        self.back_btn.setStyleSheet("min-width: 100px;")
        self.back_btn.clicked.connect(self.previous_example)
        self.button_layout.addWidget(self.back_btn)
        
        self.forward_btn = QPushButton("Forward (F)")
        self.forward_btn.setStyleSheet("min-width: 100px;")
        self.forward_btn.clicked.connect(self.next_example)
        self.button_layout.addWidget(self.forward_btn)
        
        self.delete_btn = QPushButton("Delete (Del)")
        self.delete_btn.setStyleSheet("min-width: 100px;")
        self.delete_btn.clicked.connect(self.delete_example)
        self.button_layout.addWidget(self.delete_btn)
        
        self.button_layout.addStretch(1)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.setStyleSheet("min-width: 100px; font-weight: bold;")
        self.save_btn.clicked.connect(self.save_data)
        self.button_layout.addWidget(self.save_btn)
        
        self.main_layout.addLayout(self.button_layout)
        
        # Keyboard shortcuts
        for num in range(1, 10):
            QShortcut(QKeySequence(str(num)), self, lambda n=num: self.handle_number_input(n))
            
        QShortcut(QKeySequence("B"), self, self.previous_example)
        QShortcut(QKeySequence("F"), self, self.next_example)
        QShortcut(QKeySequence(Qt.Key_Delete), self, self.delete_example)
        
        # Connect signal for checking translations
        self.check_translation_signal.connect(self.check_translation)
        
    def handle_number_input(self, number):
        if not self.fuzzy_input_mode and not self.trans_input_mode:
            self.fuzzy_input_mode = True
            self.current_fuzzy_num = number
            self.update_status_label()
            
            # Scroll to the selected fuzzy match
            if 1 <= number <= len(self.fuzzy_match_widgets):
                widget = self.fuzzy_match_widgets[number-1]
                self.scroll_area.ensureWidgetVisible(widget)
        elif self.fuzzy_input_mode:
            self.check_translation(self.current_fuzzy_num, number)
            self.reset_input_mode(new_example=False)
            
    def reset_input_mode(self,new_example=True):
        self.fuzzy_input_mode = False
        self.trans_input_mode = False
        self.current_fuzzy_num = 0
        self.current_trans_num = 0
        self.update_status_label()
        if new_example:
            self.fuzzy_match_widgets = []  # Clear references when moving to new example
        
    def update_status_label(self):
        if self.fuzzy_input_mode:
            self.status_label.setText(f"Enter translation number for fuzzy match {self.current_fuzzy_num}")
        elif self.trans_input_mode:
            self.status_label.setText(f"Checking translation {self.current_trans_num} of fuzzy match {self.current_fuzzy_num}")
        else:
            self.status_label.setText("Press a number to select fuzzy match")
            
    def check_translation(self, fuzzy_num, trans_num):
        example = self.data["examples"][self.current_index]
        fuzzy_matches = [m for m in example.get("fuzzy_matches", []) if m.get("translations")]
        
        if 1 <= fuzzy_num <= len(fuzzy_matches):
            fuzzy_match = fuzzy_matches[fuzzy_num - 1]
            translations = fuzzy_match.get("translations", [])
            
            if 1 <= trans_num <= len(translations):
                translation = translations[trans_num - 1]
                # Toggle the validated state directly in data
                translation["validated"] = not translation.get("validated", False)
                
                # Update checkbox if it exists (for current view)
                if hasattr(self, 'fuzzy_match_widgets'):
                    match_group = self.fuzzy_match_widgets[fuzzy_num-1]
                    checkboxes = match_group.findChildren(QCheckBox)
                    if trans_num-1 < len(checkboxes):
                        checkboxes[trans_num-1].setChecked(translation["validated"])
                    
    def load_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Open JSON File", "", "JSON Files (*.json)")
        if not filename:
            self.close()
            return
            
        self.filename = os.path.basename(filename)
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            self.show_example()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file: {str(e)}")
            self.close()
            
    def update_translation_text(self, translation, widget):
        """Update JSON data directly when translation text changes"""
        translation["target"] = widget.toPlainText()

    def show_example(self):
        # Clear previous widgets
        while self.scroll_layout.count():
            child = self.scroll_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        if not self.data or not self.data.get("examples"):
            return
            
        example = self.data["examples"][self.current_index]
        
        # Display main sentence
        self.main_sentence_text.setText(example.get("main_sentence", ""))
        
        # Display only fuzzy matches with translations
        fuzzy_matches = [m for m in example.get("fuzzy_matches", []) if m.get("translations")]
        
        self.fuzzy_match_widgets = []  # Store references to fuzzy match widgets
    
        for i, match in enumerate(fuzzy_matches):
            match_group = QWidget()
            self.fuzzy_match_widgets.append(match_group)  # Store reference
            match_layout = QVBoxLayout(match_group)
            match_layout.setContentsMargins(0, 10, 0, 10)
            
            # Match sentence
            sentence_label = QLabel(f"{i+1}. Fuzzy Match:")
            sentence_label.setStyleSheet("font-weight: bold; font-size: 32px;")
            match_layout.addWidget(sentence_label)
            
            sentence_text = QLineEdit()
            sentence_text.setText(match.get("sentence", ""))
            sentence_text.setReadOnly(True)
            sentence_text.setStyleSheet("font-size: 32px;")
            match_layout.addWidget(sentence_text)
            
            translations_grid = QGridLayout()
            translations_grid.setHorizontalSpacing(15)
            translations_grid.setVerticalSpacing(5)
            translations_grid.setColumnStretch(0, 0)  # Number label - don't stretch
            translations_grid.setColumnStretch(1, 0)  # Checkbox - don't stretch
            translations_grid.setColumnStretch(2, 1)  # Translation text - stretch to fill space
            
            for j, translation in enumerate(match.get("translations", [])):
                # Number label
                num_label = QLabel(f"{j+1}.")
                num_label.setStyleSheet("font-size: 32px;")
                translations_grid.addWidget(num_label, j, 0)
                
                # Checkbox for validation
                checkbox = QCheckBox()
                checkbox.setChecked(translation.get("validated", False))
                # Connect directly to data update
                checkbox.stateChanged.connect(
                    lambda state, t=translation: t.update({"validated": state == Qt.Checked})
                )
                translations_grid.addWidget(checkbox, j, 1)
                
                # Translation text
                trans_text = QTextEdit()
                trans_text.setPlainText(translation.get("target", ""))
                trans_text.setFixedHeight(trans_text.fontMetrics().lineSpacing() * 3)
                trans_text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                trans_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                trans_text.setStyleSheet("""
                    QTextEdit {
                        font-size: 32px;
                        border: 1px solid #ccc;
                        padding: 2px;
                    }
                """)
                # Connect textChanged signal to update data directly
                trans_text.textChanged.connect(
                    lambda t=translation, w=trans_text: self.update_translation_text(t, w)
                )
                translations_grid.addWidget(trans_text, j, 2)
                        
            match_layout.addLayout(translations_grid)
            self.scroll_layout.addWidget(match_group)
            
        # Add stretch to push content up
        self.scroll_layout.addStretch()
        self.update_status_label()

    def previous_example(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.reset_input_mode()
            self.show_example()
            
    def next_example(self):
        if self.data and self.current_index < len(self.data["examples"]) - 1:
            self.current_index += 1
            self.reset_input_mode()
            self.show_example()
            
    def delete_example(self):
        if not self.data or not self.data.get("examples"):
            return
            
        reply = QMessageBox.question(
            self, 
            "Delete Example", 
            "Are you sure you want to delete this example?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            del self.data["examples"][self.current_index]
            
            if self.current_index >= len(self.data["examples"]):
                self.current_index = max(0, len(self.data["examples"]) - 1)
                
            self.show_example()
            
    def save_data(self):
        if not self.data:
            return
                                    
        # Save to file
        save_filename = f"translations_validated_{self.filename}"
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Validated Translations",
            save_filename,
            "JSON Files (*.json)"
        )
        
        if save_path:
            try:
                with open(save_path, 'w', encoding='utf-8') as f:
                    json.dump(self.data, f, ensure_ascii=False, indent=2)
                QMessageBox.information(self, "Saved", f"File saved as {save_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file: {str(e)}")

if __name__ == "__main__":
    app = QApplication([])
    window = TranslationValidator()
    window.show()
    app.exec_()