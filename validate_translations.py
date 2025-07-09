import json
import sys
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QCheckBox, QPushButton, QScrollArea, QMessageBox)
from PyQt5.QtCore import Qt

class TranslationValidator(QMainWindow):
    def __init__(self, json_file_path, text_file_path):
        super().__init__()
        self.json_file_path = Path(json_file_path)
        self.text_file_path = Path(text_file_path)
        self.original_data = self.load_json()
        self.current_data = json.loads(json.dumps(self.original_data))  # Deep copy
        self.translations = self.load_translations()
        self.current_index = 0
        
        # Set larger default font size
        self.default_font = self.font()
        self.default_font.setPointSize(self.default_font.pointSize() + 4)
        self.setFont(self.default_font)
        
        self.init_ui()
        self.update_display()
        
    def load_json(self):
        with open(self.json_file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def load_translations(self):
        translations = []
        with open(self.text_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = [part.strip() for part in line.split('|||')]
                if len(parts) >= 2:
                    sentence = parts[0]
                    translations_list = parts[1:]
                    translations.append({
                        'sentence': sentence,
                        'translations': translations_list
                    })
        return translations
    
    def save_json(self):
        output_path = self.json_file_path.parent / f"translated_{self.json_file_path.name}"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.current_data, f, indent=2, ensure_ascii=False)
        QMessageBox.information(self, "Saved", f"File saved as {output_path}")
    
    def delete_current_example(self):
        current_sentence = self.translations[self.current_index]['sentence']
        
        # Find and remove all examples with matching main_sentence
        self.current_data['examples'] = [
            example for example in self.current_data.get('examples', [])
            if example.get('main_sentence') != current_sentence
        ]
        
        # Also remove from fuzzy matches in remaining examples
        for example in self.current_data.get('examples', []):
            example['fuzzy_matches'] = [
                fuzzy for fuzzy in example.get('fuzzy_matches', [])
                if fuzzy.get('sentence') != current_sentence
            ]
        
        # Remove from translations list and update display
        del self.translations[self.current_index]
        if self.current_index >= len(self.translations):
            self.current_index = max(0, len(self.translations) - 1)
        self.update_display()
    
    def init_ui(self):
        self.setWindowTitle("Translation Validator")
        self.setGeometry(100, 100, 2100, 1500)  # Larger window
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Main sentence display
        self.main_sentence_label = QLabel()
        main_sentence_font = self.main_sentence_label.font()
        main_sentence_font.setPointSize(main_sentence_font.pointSize() + 4)
        self.main_sentence_label.setFont(main_sentence_font)
        self.main_sentence_label.setStyleSheet("font-weight: bold; margin-bottom: 30px;")
        self.main_sentence_label.setWordWrap(True)
        main_layout.addWidget(self.main_sentence_label)
        
        # Translations area
        self.scroll_area = QScrollArea()
        self.scroll_area.setStyleSheet("QScrollArea { border: 2px solid gray; }")
        self.scroll_content = QWidget()
        self.translations_layout = QVBoxLayout()
        self.translations_layout.setSpacing(20)  # Increased spacing
        self.scroll_content.setLayout(self.translations_layout)
        self.scroll_area.setWidget(self.scroll_content)
        self.scroll_area.setWidgetResizable(True)
        main_layout.addWidget(self.scroll_area)
        
        # Navigation buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(30)  # Increased spacing
        
        self.back_button = QPushButton("← Back")
        self.back_button.setMinimumHeight(60)  # Larger button
        self.back_button.clicked.connect(self.prev_example)
        button_layout.addWidget(self.back_button)
        
        self.forward_button = QPushButton("Forward →")
        self.forward_button.setMinimumHeight(60)  # Larger button
        self.forward_button.clicked.connect(self.next_example)
        button_layout.addWidget(self.forward_button)
        
        self.delete_button = QPushButton("🗑 Delete")
        self.delete_button.setMinimumHeight(60)  # Larger button
        self.delete_button.clicked.connect(self.confirm_delete)
        self.delete_button.setStyleSheet("background-color: #ffcccc; font-weight: bold;")
        button_layout.addWidget(self.delete_button)
        
        self.save_button = QPushButton("💾 Save")
        self.save_button.setMinimumHeight(60)  # Larger button
        self.save_button.clicked.connect(self.save_json)
        self.save_button.setStyleSheet("background-color: #ccffcc; font-weight: bold;")
        button_layout.addWidget(self.save_button)
        
        main_layout.addLayout(button_layout)
        
        # Initialize checkboxes list
        self.checkboxes = []
    
    def confirm_delete(self):
        reply = QMessageBox.question(
            self, 'Delete Example',
            "Are you sure you want to delete this example and all its fuzzy matches?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.delete_current_example()
    
    def update_display(self):
        # Clear previous checkboxes
        for i in reversed(range(self.translations_layout.count())): 
            self.translations_layout.itemAt(i).widget().setParent(None)
        self.checkboxes = []
        
        if not self.translations:
            self.main_sentence_label.setText("No translations loaded")
            self.back_button.setEnabled(False)
            self.forward_button.setEnabled(False)
            self.save_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            return
        
        current_item = self.translations[self.current_index]
        
        # Update main sentence
        self.main_sentence_label.setText(current_item['sentence'])
        
        # Add translations with checkboxes
        for idx, translation in enumerate(current_item['translations']):
            hbox = QHBoxLayout()
            
            # Add index number (1-9)
            index_label = QLabel(f"{idx+1}.")
            index_label.setFixedWidth(40)
            index_font = index_label.font()
            index_font.setPointSize(index_font.pointSize() + 2)
            index_label.setFont(index_font)
            hbox.addWidget(index_label)
            
            checkbox = QCheckBox()
            checkbox_font = checkbox.font()
            checkbox_font.setPointSize(checkbox_font.pointSize() + 2)
            checkbox.setFont(checkbox_font)
            
            # Store the translation text in the checkbox object
            checkbox.translation_text = translation
            
            translation_label = QLabel(translation)
            translation_label.setWordWrap(True)
            translation_label.setFont(checkbox_font)
            
            # Make checkbox larger
            checkbox.setStyleSheet("""
                QCheckBox::indicator {
                    width: 30px;
                    height: 30px;
                }
            """)
            
            # Connect checkbox state change to update JSON
            checkbox.stateChanged.connect(lambda state, cb=checkbox: self.update_translation_in_json(cb))
            
            hbox.addWidget(checkbox)
            hbox.addWidget(translation_label, 1)
            
            container = QWidget()
            container.setLayout(hbox)
            self.translations_layout.addWidget(container)
            self.checkboxes.append(checkbox)
            
            # Set initial checkbox state based on existing translations
            self.set_initial_checkbox_state(checkbox, current_item['sentence'])
        
        # Update button states
        self.back_button.setEnabled(self.current_index > 0)
        self.forward_button.setEnabled(self.current_index < len(self.translations) - 1)
        self.save_button.setEnabled(True)
        self.delete_button.setEnabled(True)
    
    def set_initial_checkbox_state(self, checkbox, sentence):
        # Check if this translation already exists in the JSON data
        for example in self.current_data.get('examples', []):
            # Check main sentence
            if example.get('main_sentence') == sentence:
                if 'translations' in example:
                    for trans in example['translations']:
                        if trans.get('target') == checkbox.translation_text:
                            checkbox.setChecked(True)
                            return
                break
            
            # Check fuzzy matches
            for fuzzy in example.get('fuzzy_matches', []):
                if fuzzy.get('sentence') == sentence:
                    if 'translations' in fuzzy:
                        for trans in fuzzy['translations']:
                            if trans.get('target') == checkbox.translation_text:
                                checkbox.setChecked(True)
                                return
                    break
    
    def update_translation_in_json(self, checkbox):
        current_sentence = self.translations[self.current_index]['sentence']
        translation = checkbox.translation_text
        
        # Find all matching sentences in the JSON data
        for example in self.current_data.get('examples', []):
            # Check main sentence
            if example.get('main_sentence') == current_sentence:
                if checkbox.isChecked():
                    if 'translations' not in example:
                        example['translations'] = []
                    # Check if this translation already exists
                    if not any(t.get('target') == translation for t in example['translations']):
                        example['translations'].append({'target': translation})
                else:
                    if 'translations' in example:
                        example['translations'] = [
                            t for t in example['translations']
                            if t.get('target') != translation
                        ]
                        if not example['translations']:
                            del example['translations']
                break
            
            # Check fuzzy matches
            for fuzzy in example.get('fuzzy_matches', []):
                if fuzzy.get('sentence') == current_sentence:
                    if checkbox.isChecked():
                        if 'translations' not in fuzzy:
                            fuzzy['translations'] = []
                        # Check if this translation already exists
                        if not any(t.get('target') == translation for t in fuzzy['translations']):
                            fuzzy['translations'].append({'target': translation})
                    else:
                        if 'translations' in fuzzy:
                            fuzzy['translations'] = [
                                t for t in fuzzy['translations']
                                if t.get('target') != translation
                            ]
                            if not fuzzy['translations']:
                                del fuzzy['translations']
                    break
    
    def keyPressEvent(self, event):
        # Handle number keys 1-9 to toggle checkboxes
        if event.key() >= Qt.Key_1 and event.key() <= Qt.Key_9:
            index = event.key() - Qt.Key_1
            if index < len(self.checkboxes):
                checkbox = self.checkboxes[index]
                checkbox.setChecked(not checkbox.isChecked())
        elif event.key() == Qt.Key_B:
            if self.current_index > 0:
                self.prev_example()
        elif event.key() == Qt.Key_F:
            if self.current_index < len(self.translations) - 1:
                self.next_example()
        elif event.key() == Qt.Key_Delete:
            self.confirm_delete()
        else:
            super().keyPressEvent(event)
    
    def prev_example(self):
        self.current_index -= 1
        self.update_display()
    
    def next_example(self):
        self.current_index += 1
        self.update_display()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python translation_validator.py <json_file> <text_file>")
        print("Text file format: sentence ||| translation1 ||| translation2...")
        sys.exit(1)
    
    app = QApplication(sys.argv)
    
    # Set larger font for the entire application
    font = app.font()
    font.setPointSize(font.pointSize() + 4)
    app.setFont(font)
    
    validator = TranslationValidator(sys.argv[1], sys.argv[2])
    validator.show()
    sys.exit(app.exec_())