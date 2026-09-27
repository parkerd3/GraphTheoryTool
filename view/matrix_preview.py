"""Read-only matrix preview widget used by the main window."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QHeaderView,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
)

try:
    from ..matrices.formatting import format_scalar, matrix_to_text
except ImportError:  # Supports launching with ``python main.py``.
    from matrices.formatting import format_scalar, matrix_to_text


class MatrixPreviewTable(QTableWidget):
    """A compact matrix grid with permanent headers and checkerboard blocks."""

    INITIAL_SIZE = 15
    CELL_SIZE = 30
    BLOCK_SIZE = 5
    # Keep the checkerboard subtle and close to the dark palette inherited
    # from the operating system's current Qt theme.
    LIGHT_CELL = QColor("#343434")
    DARK_CELL = QColor("#2d2d2d")

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._matrix = np.empty((0, 0), dtype=float)
        self.setRowCount(self.INITIAL_SIZE)
        self.setColumnCount(self.INITIAL_SIZE)
        self.setMinimumHeight(170)
        self.setMinimumWidth(190)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.setAlternatingRowColors(False)
        self.setShowGrid(False)
        self.setWordWrap(False)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.horizontalHeader().setDefaultSectionSize(self.CELL_SIZE)
        self.verticalHeader().setDefaultSectionSize(self.CELL_SIZE)
        self.horizontalHeader().setFixedHeight(self.CELL_SIZE)
        self.verticalHeader().setFixedWidth(self.CELL_SIZE)
        self.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.verticalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self._entry_font = self.font()
        self._entry_font.setPointSize(max(10, self._entry_font.pointSize() + 1))
        self._populate_cells()
        self.clear_matrix()

    @property
    def matrix_shape(self) -> tuple[int, int]:
        """Return the dimensions of the currently displayed matrix."""

        return self._matrix.shape

    def set_matrix(self, matrix: np.ndarray) -> None:
        """Display ``matrix`` while retaining a small blank preview area."""

        array = np.asarray(matrix)
        if array.ndim != 2:
            raise ValueError("A matrix must be two-dimensional.")

        self._matrix = array.copy()
        rows, columns = array.shape
        capacity = max(self.INITIAL_SIZE, rows, columns)
        self.setRowCount(capacity)
        self.setColumnCount(capacity)
        self._populate_cells()

        self.setVerticalHeaderLabels(
            [str(index + 1) if index < rows else "" for index in range(capacity)]
        )
        self.setHorizontalHeaderLabels(
            [
                str(index + 1) if index < columns else ""
                for index in range(capacity)
            ]
        )

        for row in range(rows):
            for column in range(columns):
                self.item(row, column).setText(format_scalar(array[row, column]))

    def clear_matrix(self) -> None:
        """Clear matrix values while keeping the headers and grid visible."""

        self._matrix = np.empty((0, 0), dtype=float)
        capacity = max(self.INITIAL_SIZE, self.rowCount(), self.columnCount())
        self.setRowCount(capacity)
        self.setColumnCount(capacity)
        self._populate_cells()
        self.setVerticalHeaderLabels([""] * capacity)
        self.setHorizontalHeaderLabels([""] * capacity)

    def toPlainText(self) -> str:
        """Return the displayed matrix in the former text-preview format."""

        return matrix_to_text(self._matrix)

    def _populate_cells(self) -> None:
        """Create blank cells and apply the repeating 5×5 checkerboard."""

        for row in range(self.rowCount()):
            for column in range(self.columnCount()):
                item = self.item(row, column)
                if item is None:
                    item = QTableWidgetItem()
                    item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                    self.setItem(row, column, item)
                else:
                    item.setText("")
                item.setFont(self._entry_font)
                color = (
                    self.LIGHT_CELL
                    if (row // self.BLOCK_SIZE + column // self.BLOCK_SIZE) % 2 == 0
                    else self.DARK_CELL
                )
                item.setBackground(QBrush(color))

    def keyPressEvent(self, event) -> None:
        """Copy selected cells as tab-separated text for manual workflows."""

        if event.matches(QKeySequence.StandardKey.Copy):
            selected_items = self.selectedItems()
            if selected_items:
                rows = [item.row() for item in selected_items]
                columns = [item.column() for item in selected_items]
                top = min(rows)
                bottom = max(rows)
                left = min(columns)
                right = max(columns)
                copied = "\n".join(
                    "\t".join(
                        self.item(row, column).text()
                        for column in range(left, right + 1)
                    )
                    for row in range(top, bottom + 1)
                )
                QApplication.clipboard().setText(copied)
                event.accept()
                return
        super().keyPressEvent(event)
