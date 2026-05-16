"""A small PyQt5 utility for removing pages from PDF files."""

import sys
from pathlib import Path

import fitz  # PyMuPDF
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QImage, QPixmap, QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class PDFPageRemover(QWidget):
    """Main application window for visually deleting pages from a PDF."""

    THUMBNAIL_SIZE = QSize(132, 176)
    PREVIEW_ZOOM = 0.35

    def __init__(self):
        super().__init__()
        self.pdf_path = None
        self.doc = None
        self.has_unsaved_changes = False
        self.init_ui()
        self.update_actions()

    def init_ui(self):
        """Build the application interface."""
        self.setWindowTitle("PDF Page Remover")
        self.setMinimumSize(820, 640)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(24, 24, 24, 18)
        root_layout.setSpacing(18)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(16)

        title_block = QVBoxLayout()
        title_block.setSpacing(4)

        title = QLabel("PDF Page Remover")
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Load a PDF, select unwanted pages, and export a clean copy.")
        subtitle.setObjectName("SubtitleLabel")

        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        header_layout.addLayout(title_block, stretch=1)

        self.load_btn = QPushButton("Open PDF")
        self.load_btn.clicked.connect(self.load_pdf)
        self.remove_btn = QPushButton("Remove selected")
        self.remove_btn.clicked.connect(self.remove_pages)
        self.save_btn = QPushButton("Save copy")
        self.save_btn.clicked.connect(self.save_pdf)

        for button in (self.load_btn, self.remove_btn, self.save_btn):
            button.setCursor(Qt.PointingHandCursor)
            button.setMinimumHeight(38)
            header_layout.addWidget(button)

        root_layout.addLayout(header_layout)

        self.list_widget = QListWidget()
        self.list_widget.setObjectName("PageGrid")
        self.list_widget.setViewMode(QListWidget.IconMode)
        self.list_widget.setIconSize(self.THUMBNAIL_SIZE)
        self.list_widget.setGridSize(QSize(172, 224))
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setMovement(QListWidget.Static)
        self.list_widget.setSelectionMode(QListWidget.ExtendedSelection)
        self.list_widget.setUniformItemSizes(True)
        self.list_widget.itemSelectionChanged.connect(self.update_actions)
        root_layout.addWidget(self.list_widget, stretch=1)

        footer = QFrame()
        footer.setObjectName("Footer")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(14, 10, 14, 10)

        self.status_label = QLabel("Open a PDF to get started.")
        self.status_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.selection_label = QLabel("No selection")

        footer_layout.addWidget(self.status_label)
        footer_layout.addWidget(self.selection_label)
        root_layout.addWidget(footer)

        self.apply_modern_theme()

    def apply_modern_theme(self):
        """Apply lightweight styling without external dependencies."""
        self.setStyleSheet(
            """
            QWidget {
                background: #f8fafc;
                color: #0f172a;
                font-family: Inter, Segoe UI, Arial, sans-serif;
                font-size: 14px;
            }
            QLabel#TitleLabel {
                font-size: 28px;
                font-weight: 700;
                letter-spacing: -0.4px;
            }
            QLabel#SubtitleLabel {
                color: #64748b;
                font-size: 14px;
            }
            QPushButton {
                background: #2563eb;
                border: 0;
                border-radius: 9px;
                color: white;
                font-weight: 600;
                padding: 8px 14px;
            }
            QPushButton:hover { background: #1d4ed8; }
            QPushButton:pressed { background: #1e40af; }
            QPushButton:disabled {
                background: #cbd5e1;
                color: #64748b;
            }
            QListWidget#PageGrid {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 16px;
                padding: 14px;
                outline: 0;
            }
            QListWidget#PageGrid::item {
                border: 1px solid transparent;
                border-radius: 12px;
                margin: 8px;
                padding: 8px;
            }
            QListWidget#PageGrid::item:hover {
                background: #eff6ff;
                border-color: #bfdbfe;
            }
            QListWidget#PageGrid::item:selected {
                background: #dbeafe;
                border-color: #2563eb;
                color: #1e3a8a;
            }
            QFrame#Footer {
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
            }
            """
        )

    def load_pdf(self):
        """Load the selected PDF and render thumbnails in memory."""
        if not self.confirm_discard_changes():
            return

        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open PDF File",
            "",
            "PDF Files (*.pdf)",
        )

        if not file_name:
            return

        try:
            new_doc = fitz.open(file_name)
        except (RuntimeError, ValueError) as error:
            QMessageBox.critical(self, "Unable to open PDF", str(error))
            return

        self.close_document()
        self.pdf_path = Path(file_name)
        self.doc = new_doc
        self.has_unsaved_changes = False
        self.refresh_thumbnails()

    def refresh_thumbnails(self):
        """Refresh the page grid for the current document."""
        self.list_widget.setUpdatesEnabled(False)
        self.list_widget.clear()

        if not self.doc:
            self.list_widget.setUpdatesEnabled(True)
            self.update_actions()
            return

        for page_index in range(self.doc.page_count):
            pixmap = self.render_page_thumbnail(page_index)
            self.add_thumbnail(pixmap, page_index)

        self.list_widget.setUpdatesEnabled(True)
        self.update_actions()

    def render_page_thumbnail(self, page_index):
        """Render a single page thumbnail directly to a QPixmap."""
        page = self.doc.load_page(page_index)
        pix = page.get_pixmap(
            matrix=fitz.Matrix(self.PREVIEW_ZOOM, self.PREVIEW_ZOOM),
            alpha=False,
        )
        image = QImage(
            pix.samples,
            pix.width,
            pix.height,
            pix.stride,
            QImage.Format_RGB888,
        ).copy()
        return QPixmap.fromImage(image).scaled(
            self.THUMBNAIL_SIZE,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

    def add_thumbnail(self, pixmap, page_index):
        """Add a rendered thumbnail to the page grid."""
        item = QListWidgetItem(QIcon(pixmap), f"Page {page_index + 1}")
        item.setData(Qt.UserRole, page_index)
        item.setTextAlignment(Qt.AlignCenter)
        item.setToolTip(f"Page {page_index + 1}")
        self.list_widget.addItem(item)

    def remove_pages(self):
        """Remove selected pages and re-render the updated document."""
        if not self.doc:
            QMessageBox.warning(self, "No PDF loaded", "Open a PDF before removing pages.")
            return

        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No pages selected", "Select one or more pages to remove.")
            return

        pages_to_remove = sorted(
            (item.data(Qt.UserRole) for item in selected_items),
            reverse=True,
        )

        if len(pages_to_remove) == self.doc.page_count:
            QMessageBox.warning(
                self,
                "Cannot remove every page",
                "A PDF must contain at least one page. Leave one page in the document.",
            )
            return

        for page_num in pages_to_remove:
            self.doc.delete_page(page_num)

        self.has_unsaved_changes = True
        self.refresh_thumbnails()

    def save_pdf(self):
        """Save the modified document to a new file."""
        if not self.doc:
            QMessageBox.warning(self, "No PDF loaded", "Open a PDF before saving.")
            return

        default_name = "edited.pdf"
        if self.pdf_path:
            default_name = f"{self.pdf_path.stem}-edited.pdf"

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save PDF File",
            default_name,
            "PDF Files (*.pdf)",
        )

        if not save_path:
            return

        output_path = Path(save_path).with_suffix(".pdf")

        try:
            self.doc.save(output_path, garbage=4, deflate=True, clean=True)
        except (RuntimeError, ValueError) as error:
            QMessageBox.critical(self, "Unable to save PDF", str(error))
            return

        self.has_unsaved_changes = False
        self.update_actions()
        QMessageBox.information(self, "Saved", f"PDF saved to:\n{output_path}")

    def update_actions(self):
        """Keep buttons and status text synchronized with the app state."""
        has_document = self.doc is not None
        selected_count = len(self.list_widget.selectedItems())
        page_count = self.doc.page_count if self.doc else 0

        self.remove_btn.setEnabled(has_document and selected_count > 0)
        self.save_btn.setEnabled(has_document)

        if has_document:
            name = self.pdf_path.name if self.pdf_path else "Untitled PDF"
            changed = " • unsaved changes" if self.has_unsaved_changes else ""
            self.status_label.setText(f"{name} • {page_count} page(s){changed}")
        else:
            self.status_label.setText("Open a PDF to get started.")

        if selected_count:
            self.selection_label.setText(f"{selected_count} selected")
        else:
            self.selection_label.setText("No selection")

    def confirm_discard_changes(self):
        """Ask before replacing or closing a document with unsaved edits."""
        if not self.has_unsaved_changes:
            return True

        response = QMessageBox.question(
            self,
            "Discard unsaved changes?",
            "You have unsaved changes. Do you want to discard them?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return response == QMessageBox.Yes

    def close_document(self):
        """Close the active PyMuPDF document if one is open."""
        if self.doc is not None:
            self.doc.close()
        self.doc = None
        self.pdf_path = None
        self.has_unsaved_changes = False

    def closeEvent(self, event):
        """Prompt for unsaved work and release the PDF handle on exit."""
        if not self.confirm_discard_changes():
            event.ignore()
            return

        self.close_document()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PDFPageRemover()
    window.show()
    sys.exit(app.exec_())
