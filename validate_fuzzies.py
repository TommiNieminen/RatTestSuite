import json
import sys
import re
from pathlib import Path
from difflib import SequenceMatcher
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QCheckBox, QPushButton, QScrollArea, QMessageBox, QSizePolicy)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTextCursor, QTextCharFormat, QColor, QTextDocument

class FuzzyMatchValidator(QMainWindow):
    def __init__(self, json_file_path):
        super().__init__()
        self.json_file_path = Path(json_file_path)
        self.original_data = self.load_json()
        self.current_data = json.loads(json.dumps(self.original_data))
        self.current_index = 0
        
        # Set larger default font size
        self.default_font = self.font()
        self.default_font.setPointSize(self.default_font.pointSize())
        self.setFont(self.default_font)
        
        self.init_ui()
        self.update_display()
        
    def load_json(self):
        with open(self.json_file_path, 'r') as f:
            return json.load(f)
    
    def save_json(self):
        output_path = self.json_file_path.parent / f"validated_{self.json_file_path.name}"
        with open(output_path, 'w') as f:
            json.dump(self.current_data, f, indent=2)
        QMessageBox.information(self, "Saved", f"File saved as {output_path}")
    
    def highlight_word_differences(self, main_sentence, fuzzy_sentence):
        # Tokenize both sentences into words (including punctuation as separate tokens)
        main_words = re.findall(r"\w+|\s+|\W", main_sentence)
        fuzzy_words = re.findall(r"\w+|\s+|\W", fuzzy_sentence)
        
        # Create a QTextDocument to format the text
        doc = QTextDocument()
        cursor = QTextCursor(doc)
        
        # Default format (for unchanged text)
        default_format = QTextCharFormat()
        
        # Format for additions (light blue background)
        add_format = QTextCharFormat()
        add_format.setBackground(QColor(173, 216, 230))  # Light blue
        add_format.setFontItalic(True)
        
        # Format for deletions (strikethrough)
        del_format = QTextCharFormat()
        del_format.setFontStrikeOut(True)
        del_format.setForeground(QColor(150, 150, 150))  # Gray
        
        # Use SequenceMatcher to find word-level differences
        matcher = SequenceMatcher(None, main_words, fuzzy_words)
        
        for op in matcher.get_opcodes():
            tag, i1, i2, j1, j2 = op
            
            if tag == 'equal':
                # Insert unchanged words with default format
                for word in fuzzy_words[j1:j2]:
                    cursor.insertText(word, default_format)
            elif tag == 'insert':
                # Insert added words with add format
                for word in fuzzy_words[j1:j2]:
                    cursor.insertText(word, add_format)
            elif tag == 'delete':
                # Insert deleted words with del format
                for word in main_words[i1:i2]:
                    cursor.insertText(word, del_format)
            elif tag == 'replace':
                # Insert deleted words from main with del format
                for word in main_words[i1:i2]:
                    cursor.insertText(word, del_format)
                # Insert added words from fuzzy with add format
                for word in fuzzy_words[j1:j2]:
                    cursor.insertText(word, add_format)
        
        return doc
    
    def init_ui(self):
        self.setWindowTitle("Fuzzy Match Validator")
        self.setGeometry(100, 100, 2100, 1600)  # Fixed window size
        self.setFixedWidth(2500)  # Prevent horizontal resizing

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Main sentence display
        self.main_sentence_label = QLabel()
        main_sentence_font = self.main_sentence_label.font()
        main_sentence_font.setPointSize(main_sentence_font.pointSize())
        self.main_sentence_label.setFont(main_sentence_font)
        self.main_sentence_label.setStyleSheet("font-weight: bold; margin-bottom: 30px;")
        main_layout.addWidget(self.main_sentence_label)
        
        # Position indicator
        self.position_label = QLabel()
        position_font = self.position_label.font()
        position_font.setPointSize(position_font.pointSize())
        self.position_label.setFont(position_font)
        self.position_label.setStyleSheet("color: #666; margin-bottom: 10px;")
        main_layout.addWidget(self.position_label)
        
        # Domain and length category
        self.metadata_label = QLabel()
        metadata_font = self.metadata_label.font()
        metadata_font.setPointSize(metadata_font.pointSize())
        self.metadata_label.setFont(metadata_font)
        self.metadata_label.setStyleSheet("color: #666; margin-bottom: 30px;")
        main_layout.addWidget(self.metadata_label)
        
        # Fuzzy matches area
        self.scroll_area = QScrollArea()
        self.scroll_area.setStyleSheet("QScrollArea { border: 2px solid gray; }")
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # Disable horizontal scroll
        self.scroll_content = QWidget()
        self.fuzzy_layout = QVBoxLayout()
        self.fuzzy_layout.setSpacing(20)
        self.scroll_content.setLayout(self.fuzzy_layout)
        self.scroll_area.setWidget(self.scroll_content)
        self.scroll_area.setWidgetResizable(True)
        main_layout.addWidget(self.scroll_area)        
        
        # Navigation buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(30)  # Increased spacing
        
        self.back_button = QPushButton("← Back (B)")
        self.back_button.setMinimumHeight(60)  # Larger button
        self.back_button.clicked.connect(self.prev_example)
        button_layout.addWidget(self.back_button)
        
        self.forward_button = QPushButton("Forward (F) →")
        self.forward_button.setMinimumHeight(60)  # Larger button
        self.forward_button.clicked.connect(self.next_example)
        button_layout.addWidget(self.forward_button)
        
        self.delete_button = QPushButton("✗ Delete (Del)")
        self.delete_button.setMinimumHeight(60)  # Larger button
        self.delete_button.clicked.connect(self.delete_example)
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
        self.fuzzy_labels = []
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            self.delete_example()
        elif event.key() == Qt.Key_F:
            self.next_example()
        elif event.key() == Qt.Key_B:
            self.prev_example()
        elif Qt.Key_1 <= event.key() <= Qt.Key_9:
            index = event.key() - Qt.Key_1
            if index < len(self.checkboxes):
                checkbox = self.checkboxes[index]
                checkbox.setChecked(not checkbox.isChecked())
        else:
            super().keyPressEvent(event)
    
    def update_display(self):
        # Clear previous widgets
        for i in reversed(range(self.fuzzy_layout.count())): 
            self.fuzzy_layout.itemAt(i).widget().setParent(None)
        self.checkboxes = []
        self.fuzzy_labels = []
        
        if not self.current_data["examples"]:
            self.main_sentence_label.setText("No examples remaining")
            self.position_label.setText("")
            self.metadata_label.setText("")
            self.back_button.setEnabled(False)
            self.forward_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            return
        
        example = self.current_data["examples"][self.current_index]
        main_sentence = example["main_sentence"]
        
        # Update main sentence and metadata
        self.main_sentence_label.setText(main_sentence)
        self.position_label.setText(f"Example {self.current_index + 1} of {len(self.current_data['examples'])}")
        
        # Add fuzzy matches with checkboxes
        for i, fuzzy in enumerate(example["fuzzy_matches"], start=1):  # Start index at 1
            # Create a horizontal container for checkbox and sentence
            container = QWidget()
            container_layout = QHBoxLayout()
            container.setLayout(container_layout)
            
            # Create checkbox with index number
            checkbox = QCheckBox(f"{i}.")  # Add index number here
            checkbox_font = checkbox.font()
            checkbox_font.setPointSize(checkbox_font.pointSize())
            checkbox.setFont(checkbox_font)
            checkbox.setChecked(fuzzy.get("validated", False))
            
            checkbox.setStyleSheet("""
                QCheckBox {
                    spacing: 15px;
                    margin-right: 10px;
                    min-width: 40px;
                }
                QCheckBox::indicator {
                    width: 30px;
                    height: 30px;
                }
            """)
            
            container_layout.addWidget(checkbox)
            self.checkboxes.append(checkbox)
            
            # Create label for the highlighted differences with proper wrapping
            fuzzy_label = QLabel()
            fuzzy_label.setWordWrap(True)
            fuzzy_label_font = fuzzy_label.font()
            fuzzy_label_font.setPointSize(fuzzy_label_font.pointSize())
            fuzzy_label.setFont(fuzzy_label_font)
            fuzzy_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            
            # Highlight word-level differences
            doc = self.highlight_word_differences(main_sentence, fuzzy['sentence'])
            fuzzy_label.setText(doc.toHtml())
            
            # Add stretchable spacer to ensure proper wrapping
            container_layout.addWidget(fuzzy_label, stretch=1)
            self.fuzzy_labels.append(fuzzy_label)
            
            # Add the container to the main layout
            self.fuzzy_layout.addWidget(container)   
    
    def save_current_selections(self):
        if not self.current_data["examples"]:
            return
            
        example = self.current_data["examples"][self.current_index]
        for i, fuzzy in enumerate(example["fuzzy_matches"]):
            fuzzy["validated"] = self.checkboxes[i].isChecked()
    
    def prev_example(self):
        self.save_current_selections()
        if self.current_index > 0:
            self.current_index -= 1
            self.update_display()
    
    def next_example(self):
        self.save_current_selections()
        if self.current_index < len(self.current_data["examples"]) - 1:
            self.current_index += 1
            self.update_display()
    
    def delete_example(self):
        if not self.current_data["examples"]:
            return
            
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Delete Example")
        msg_box.setText("Are you sure you want to delete this example and all its fuzzy matches?")
        
        # Make message box larger
        msg_box_font = msg_box.font()
        msg_box_font.setPointSize(msg_box_font.pointSize() * 2)
        msg_box.setFont(msg_box_font)
        
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)
        
        # Make buttons larger
        for button in msg_box.buttons():
            button.setMinimumSize(200, 60)
        
        reply = msg_box.exec_()
        
        if reply == QMessageBox.Yes:
            del self.current_data["examples"][self.current_index]
            
            # Adjust current_index if we deleted the last example
            if self.current_index >= len(self.current_data["examples"]):
                self.current_index = max(0, len(self.current_data["examples"]) - 1)
            
            self.update_display()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python fuzzy_validator.py <json_file>")
        sys.exit(1)
    
    app = QApplication(sys.argv)
    
    # Set larger font for the entire application
    font = app.font()
    font.setPointSize(font.pointSize()*2)
    app.setFont(font)
    
    validator = FuzzyMatchValidator(sys.argv[1])
    validator.show()
    sys.exit(app.exec_())