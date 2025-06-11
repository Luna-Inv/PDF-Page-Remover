# PDF PAGE REMOVER
import sys
import fitz  # PyMuPDF
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog,
    QListWidget, QMessageBox, QListWidgetItem
)
from PyQt5.QtGui import QPixmap, QImage, QIcon
from PyQt5.QtCore import Qt
import tempfile
import os


class PDFPageRemover(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.pdf_path = None
        self.doc = None
        self.temp_images = []  # Store temp images for cleanup
        self.page_map = []  # Track page indices for UI sync

    def initUI(self):
        self.setWindowTitle("PDF Page Remover")
        self.setGeometry(100, 100, 600, 600)

        layout = QVBoxLayout()

        self.load_btn = QPushButton("Load PDF")
        self.load_btn.clicked.connect(self.load_pdf)
        layout.addWidget(self.load_btn)

        self.list_widget = QListWidget()
        self.list_widget.setViewMode(QListWidget.IconMode)  # Display images
        self.list_widget.setIconSize(QPixmap(100, 140).size())  # Thumbnail size
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setSelectionMode(QListWidget.MultiSelection)  # Allow multiple selections
        layout.addWidget(self.list_widget)

        self.remove_btn = QPushButton("Remove Selected Pages")
        self.remove_btn.clicked.connect(self.remove_pages)
        layout.addWidget(self.remove_btn)

        self.save_btn = QPushButton("Save PDF")
        self.save_btn.clicked.connect(self.save_pdf)
        layout.addWidget(self.save_btn)

        self.setLayout(layout)

    def load_pdf(self):
        """Loads the PDF and renders thumbnails."""
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Open PDF File", "", "PDF Files (*.pdf)", options=options)

        if file_name:
            self.pdf_path = file_name
            self.doc = fitz.open(file_name)
            self.refresh_thumbnails()

    def refresh_thumbnails(self):
        """Refreshes the GUI with the current state of the PDF."""
        self.list_widget.clear()
        self.temp_images = []  # Reset temp images
        self.page_map = list(range(len(self.doc)))  # Track original page indices

        for i, page in enumerate(self.doc):
            img_path = self.render_page_as_image(page, i)
            if img_path:
                self.temp_images.append(img_path)  # Store temp file paths
                self.add_thumbnail(img_path, i)

    def render_page_as_image(self, page, index):
        """Render PDF page as image and save to a temporary file."""
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))  # Higher DPI for clarity
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)

        temp_dir = tempfile.gettempdir()
        img_path = os.path.join(temp_dir, f"pdf_page_{index}.png")
        img.save(img_path)

        return img_path

    def add_thumbnail(self, img_path, index):
        """Add thumbnail to the QListWidget."""
        item = QListWidgetItem(QIcon(img_path), f"Page {index + 1}")
        item.setData(Qt.UserRole, index)  # Store page index
        self.list_widget.addItem(item)

    def remove_pages(self):
        """Removes selected pages from the document and updates the GUI."""
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Warning", "No pages selected!")
            return

        # Get the actual page indices in descending order (to prevent shifting issues)
        pages_to_remove = sorted([item.data(Qt.UserRole) for item in selected_items], reverse=True)

        # Remove pages from document
        for page_num in pages_to_remove:
            self.doc.delete_page(page_num)

        # Update the thumbnails list (without reloading the file)
        self.refresh_thumbnails()

    def save_pdf(self):
        """Saves the modified PDF to a new file."""
        if not self.doc:
            QMessageBox.warning(self, "Warning", "No PDF loaded!")
            return

        options = QFileDialog.Options()
        save_path, _ = QFileDialog.getSaveFileName(self, "Save PDF File", "", "PDF Files (*.pdf)", options=options)

        if save_path:
            self.doc.save(save_path)
            self.doc.close()
            QMessageBox.information(self, "Success", "PDF saved successfully!")

        # Cleanup temporary images
        for img in self.temp_images:
            if os.path.exists(img):
                os.remove(img)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PDFPageRemover()
    window.show()
    sys.exit(app.exec_())
