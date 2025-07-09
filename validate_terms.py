import json
import sys
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QCheckBox, QPushButton, QScrollArea, QMessageBox, QGroupBox)
from PyQt5.QtCore import Qt, QTimer

class TermValidator(QMainWindow):
    def __init__(self, json_file_path):
        super().__init__()
        self.json_file_path = Path(json_file_path)
        self.original_data = self.load_json()
        self.current_data = json.loads(json.dumps(self.original_data))  # Deep copy
        self.current_index = 0
        self.selected_term_index = None  # Track which term is in selection mode
        self.deleted_examples = set()  # Track deleted examples
        self.term_widgets = []  # Store references to term group boxes
        self.current_term_scroll_index = 0  # Track which term is at the top
        
        # Set larger default font size
        self.default_font = self.font()
        self.default_font.setPointSize(self.default_font.pointSize() + 6)
        self.setFont(self.default_font)
        
        self.init_ui()
        self.update_display()
        
    def load_json(self):
        with open(self.json_file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_validated_terms(self):
        output_path = self.json_file_path.parent / f"validated_terms_{self.json_file_path.name}"
        
        # Create output data from current_data which has all the checkbox states
        output_data = json.loads(json.dumps(self.current_data))
        
        # Filter examples - remove deleted ones
        output_data['examples'] = [
            ex for i, ex in enumerate(output_data.get('examples', []))
            if i not in self.deleted_examples
        ]
        
        # For each remaining example, filter terms to only include those with at least one selected translation
        for example in output_data.get('examples', []):
            if 'terms' in example:
                # Create a new terms dictionary with only validated terms
                new_terms = {}
                for term, translations in example['terms'].items():
                    # Filter translations to only include selected ones
                    selected_translations = [t for t in translations if t.get('selected', False)]
                    if selected_translations:
                        new_terms[term] = selected_translations
                example['terms'] = new_terms
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        QMessageBox.information(self, "Saved", f"File saved as {output_path}")
    
    def delete_current_example(self):
        self.deleted_examples.add(self.current_index)
        self.current_index = min(self.current_index, len(self.original_data.get('examples', [])) - 1)
        if len(self.deleted_examples) >= len(self.original_data.get('examples', [])):
            QMessageBox.information(self, "No More Examples", "All examples have been deleted.")
            self.close()
        else:
            self.update_display()
    
    def init_ui(self):
        self.setWindowTitle("Term Translation Validator")
        self.setGeometry(100, 100, 2400, 1600)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Main sentence display
        self.main_sentence_label = QLabel()
        main_sentence_font = self.main_sentence_label.font()
        main_sentence_font.setPointSize(main_sentence_font.pointSize() + 8)
        self.main_sentence_label.setFont(main_sentence_font)
        self.main_sentence_label.setStyleSheet("""
            font-weight: bold; 
            margin-bottom: 30px;
            padding: 15px;
            background-color: #f0f0f0;
            border-radius: 10px;
        """)
        self.main_sentence_label.setWordWrap(True)
        main_layout.addWidget(self.main_sentence_label)
        
        # Terms area
        self.scroll_area = QScrollArea()
        self.scroll_area.setStyleSheet("""
            QScrollArea { 
                border: 2px solid gray;
                border-radius: 10px;
            }
        """)
        self.scroll_content = QWidget()
        self.terms_layout = QVBoxLayout()
        self.terms_layout.setSpacing(25)
        self.terms_layout.setContentsMargins(15, 15, 15, 15)
        self.scroll_content.setLayout(self.terms_layout)
        self.scroll_area.setWidget(self.scroll_content)
        self.scroll_area.setWidgetResizable(True)
        main_layout.addWidget(self.scroll_area, 1)
        
        # Status label
        self.status_label = QLabel()
        self.status_label.setStyleSheet("""
            color: #555555; 
            font-style: italic;
            font-size: 16px;
            padding: 10px;
        """)
        main_layout.addWidget(self.status_label)
        
        # Navigation buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(30)
        
        self.back_button = QPushButton("← Back (b)")
        self.back_button.setStyleSheet("""
            QPushButton {
                font-size: 18px;
                padding: 15px;
                min-width: 150px;
            }
        """)
        self.back_button.clicked.connect(self.prev_example)
        button_layout.addWidget(self.back_button)
        
        self.forward_button = QPushButton("Forward (f) →")
        self.forward_button.setStyleSheet("""
            QPushButton {
                font-size: 18px;
                padding: 15px;
                min-width: 150px;
            }
        """)
        self.forward_button.clicked.connect(self.next_example)
        button_layout.addWidget(self.forward_button)
        
        self.delete_button = QPushButton("🗑 Delete (Del)")
        self.delete_button.setStyleSheet("""
            QPushButton {
                font-size: 18px;
                padding: 15px;
                min-width: 150px;
                background-color: #ffcccc;
                font-weight: bold;
            }
        """)
        self.delete_button.clicked.connect(self.delete_current_example)  # Removed confirm_delete
        button_layout.addWidget(self.delete_button)
        
        self.save_button = QPushButton("💾 Save")
        self.save_button.setStyleSheet("""
            QPushButton {
                font-size: 18px;
                padding: 15px;
                min-width: 150px;
                background-color: #ccffcc;
                font-weight: bold;
            }
        """)
        self.save_button.clicked.connect(self.save_validated_terms)
        button_layout.addWidget(self.save_button)
        
        main_layout.addLayout(button_layout)
    def update_display(self):
        # Clear previous widgets
        for i in reversed(range(self.terms_layout.count())): 
            self.terms_layout.itemAt(i).widget().setParent(None)
        self.term_widgets = []
        
        examples = self.current_data.get('examples', [])
        if not examples:
            self.main_sentence_label.setText("No examples found in JSON file")
            self.back_button.setEnabled(False)
            self.forward_button.setEnabled(False)
            self.save_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            return
        
        # Skip deleted examples
        while self.current_index in self.deleted_examples:
            self.current_index = (self.current_index + 1) % len(examples)
        
        current_example = examples[self.current_index]
        
        # Update main sentence
        main_sentence = current_example.get('main_sentence', '').strip()
        self.main_sentence_label.setText(main_sentence)
        
        # Add terms and their translations
        if 'terms' in current_example:
            terms = current_example['terms']
            term_keys = list(terms.keys())
            
            for term_idx, (term, translations) in enumerate(terms.items()):
                term_group = QGroupBox(f"{term_idx+1}. {term}")
                term_group.setStyleSheet("""
                    QGroupBox { 
                        font-weight: bold; 
                        font-size: 18px;
                        margin-top: 15px;
                    }
                    QGroupBox::title {
                        subcontrol-origin: margin;
                        left: 10px;
                        padding: 0 5px;
                    }
                """)
                term_layout = QVBoxLayout()
                term_layout.setSpacing(15)
                
                for trans_idx, translation in enumerate(translations):
                    hbox = QHBoxLayout()
                    hbox.setSpacing(20)
                    
                    # Add translation index (1-9)
                    index_label = QLabel(f"{trans_idx+1}.")
                    index_label.setFixedWidth(40)
                    index_font = index_label.font()
                    index_font.setPointSize(16)
                    index_label.setFont(index_font)
                    hbox.addWidget(index_label)
                    
                    checkbox = QCheckBox()
                    # Get the saved state from current_data
                    checkbox.setChecked(translation.get('selected', False))
                    checkbox.setStyleSheet("""
                        QCheckBox::indicator {
                            width: 30px;
                            height: 30px;
                        }
                    """)
                    
                    # Store references to term and translation indices
                    checkbox.term_idx = term_idx
                    checkbox.trans_idx = trans_idx
                    
                    # Connect checkbox state change
                    checkbox.stateChanged.connect(self.update_translation_selection)
                    
                    # Create widget for translation and test
                    trans_test_widget = QWidget()
                    trans_test_layout = QVBoxLayout()
                    trans_test_layout.setSpacing(5)
                    
                    # Translation label
                    target_label = QLabel(translation['target'])
                    target_label.setWordWrap(True)
                    target_font = target_label.font()
                    target_font.setPointSize(16)
                    target_label.setFont(target_font)
                    trans_test_layout.addWidget(target_label)
                    
                    # Test label (if tests exist)
                    if 'tests' in translation and translation['tests']:
                        test_label = QLabel()
                        test_label.setWordWrap(True)
                        test_font = test_label.font()
                        test_font.setPointSize(14)
                        test_label.setFont(test_font)
                        test_label.setStyleSheet("color: #666666; font-style: italic;")
                        
                        test_texts = []
                        for test in translation['tests']:
                            if test['type'] == 'term_present':
                                test_texts.append(f"Must contain: {test['condition']}")
                        
                        test_label.setText("\n".join(test_texts))
                        trans_test_layout.addWidget(test_label)
                    
                    trans_test_widget.setLayout(trans_test_layout)
                    
                    hbox.addWidget(checkbox)
                    hbox.addWidget(trans_test_widget, 1)
                    
                    container = QWidget()
                    container.setLayout(hbox)
                    term_layout.addWidget(container)
                
                term_group.setLayout(term_layout)
                self.terms_layout.addWidget(term_group)
                self.term_widgets.append(term_group)
        
        # Update status
        self.status_label.setText(f"Example {self.current_index + 1} of {len(examples)}. Press number keys to select terms/translations.")
        
        # Update button states
        self.back_button.setEnabled(self.current_index > 0)
        self.forward_button.setEnabled(self.current_index < len(examples) - 1)
        self.save_button.setEnabled(True)
        self.delete_button.setEnabled(True)
        
        # Reset selection mode and scroll position
        self.selected_term_index = None
        self.current_term_scroll_index = 0
        self.scroll_to_current_term()

    def update_translation_selection(self, state):
        checkbox = self.sender()
        term_idx = checkbox.term_idx
        trans_idx = checkbox.trans_idx
        
        # Update the current_data dict immediately
        examples = self.current_data.get('examples', [])
        if examples and self.current_index < len(examples):
            current_example = examples[self.current_index]
            if 'terms' in current_example:
                term_keys = list(current_example['terms'].keys())
                if term_idx < len(term_keys):
                    term = term_keys[term_idx]
                    translations = current_example['terms'][term]
                    if trans_idx < len(translations):
                        translations[trans_idx]['selected'] = (state == Qt.Checked)
    
    def scroll_to_current_term(self):
        """Scroll to make the current term visible at the top"""
        if not self.term_widgets or self.current_term_scroll_index >= len(self.term_widgets):
            return
            
        # Use a timer to ensure the widget is properly laid out before scrolling
        QTimer.singleShot(100, lambda: self._perform_scroll_to_term())
    
    def _perform_scroll_to_term(self):
        """Actual scrolling implementation"""
        if self.current_term_scroll_index < len(self.term_widgets):
            term_widget = self.term_widgets[self.current_term_scroll_index]
            # Calculate the position to scroll to
            scroll_pos = term_widget.y()
            self.scroll_area.verticalScrollBar().setValue(scroll_pos)
    
    def scroll_to_next_term(self):
        """Scroll to the next term in the list"""
        if self.term_widgets and self.current_term_scroll_index < len(self.term_widgets) - 1:
            self.current_term_scroll_index += 1
            self.scroll_to_current_term()
    
    def keyPressEvent(self, event):
        examples = self.original_data.get('examples', [])
        if not examples:
            return
            
        # Handle navigation keys in both normal and selection modes
        if event.key() == Qt.Key_B:
            self.prev_example()
            return
        elif event.key() == Qt.Key_F:
            self.next_example()
            return
        elif event.key() == Qt.Key_Delete:
            self.delete_current_example()
            return
        elif event.key() == Qt.Key_N:
            self.scroll_to_next_term()
            return
            
        if self.selected_term_index is None:
            # Normal mode - number keys select terms
            if event.key() >= Qt.Key_1 and event.key() <= Qt.Key_9:
                term_idx = event.key() - Qt.Key_1
                if term_idx < len(self.term_widgets):
                    self.selected_term_index = term_idx
                    self.update_status(f"Selecting translations for term {term_idx+1}. Press number keys (1-9) to toggle translations, Esc to exit.")
            else:
                super().keyPressEvent(event)
        else:
            # Translation selection mode - number keys toggle translations
            if event.key() >= Qt.Key_1 and event.key() <= Qt.Key_9:
                trans_idx = event.key() - Qt.Key_1
                current_example = examples[self.current_index]
                if 'terms' in current_example:
                    term_keys = list(current_example['terms'].keys())
                    if self.selected_term_index < len(term_keys):
                        term = term_keys[self.selected_term_index]
                        translations = current_example['terms'][term]
                        if trans_idx < len(translations):
                            # Find the corresponding checkbox and toggle it
                            term_group = self.term_widgets[self.selected_term_index]
                            layout = term_group.layout()
                            trans_widget = layout.itemAt(trans_idx).widget()
                            checkbox = trans_widget.layout().itemAt(1).widget()  # Checkbox is at position 1 (after index label)
                            checkbox.setChecked(not checkbox.isChecked())
            elif event.key() == Qt.Key_Escape:
                self.selected_term_index = None
                self.update_status(f"Example {self.current_index + 1} of {len(examples)}. Press number keys to select terms/translations.")
            else:
                super().keyPressEvent(event)
    
    def update_status(self, message):
        self.status_label.setText(message)
    
    def prev_example(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.update_display()
    
    def next_example(self):
        examples = self.original_data.get('examples', [])
        if self.current_index < len(examples) - 1:
            self.current_index += 1
            self.update_display()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python term_validator.py <json_file>")
        sys.exit(1)
    
    app = QApplication(sys.argv)
    
    # Set larger font for the entire application
    font = app.font()
    font.setPointSize(font.pointSize() + 4)
    app.setFont(font)
    
    validator = TermValidator(sys.argv[1])
    validator.show()
    sys.exit(app.exec_())