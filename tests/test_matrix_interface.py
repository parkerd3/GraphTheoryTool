import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from GraphTheoryTool.matrices import matrix_to_mathematica, matrix_to_text
from GraphTheoryTool.view.main_window import MainWindow


def get_qapplication() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_matrix_formatters_create_readable_and_mathematica_text() -> None:
    matrix = np.array([[0.0, 1.0], [1.0, 2.5]])

    assert matrix_to_text(matrix) == "0 1\n1 2.5"
    assert matrix_to_mathematica(matrix) == "{{0,1},{1,2.5}}"


def test_main_window_generates_and_copies_adjacency_matrix() -> None:
    get_qapplication()
    window = MainWindow()
    assert [
        window.matrix_type_combo.itemData(index)
        for index in range(window.matrix_type_combo.count())
    ] == ["adjacency", "degree", "laplacian", "ihara"]
    first = window.graph.add_node(100, 100)
    second = window.graph.add_node(300, 100)
    window.scene.add_node_visual(first)
    window.scene.add_node_visual(second)
    edge = window.graph.add_edge(first.id, second.id)
    window.scene.add_edge_visual(edge)

    window.matrix_button.click()

    assert window.matrix_preview.toPlainText() == "0 1\n1 0"
    assert window.matrix_preview.horizontalHeaderItem(0).text() == "1"
    assert window.matrix_preview.horizontalHeaderItem(1).text() == "2"
    assert window.matrix_preview.horizontalHeaderItem(2).text() == ""
    assert window.matrix_preview.verticalHeaderItem(0).text() == "1"
    assert window.matrix_preview.verticalHeaderItem(1).text() == "2"
    assert window.matrix_preview.verticalHeaderItem(2).text() == ""
    assert not window.matrix_preview.showGrid()
    assert window.matrix_preview.verticalHeader().width() == 30
    assert window.matrix_preview.horizontalHeader().height() == 30
    assert window.matrix_preview.sizePolicy().verticalPolicy().name == "Expanding"
    assert window.matrix_preview.item(0, 0).font().pointSize() >= 10
    assert (
        window.matrix_preview.item(0, 0).background().color()
        == window.matrix_preview.item(4, 4).background().color()
    )
    assert (
        window.matrix_preview.item(0, 0).background().color()
        != window.matrix_preview.item(0, 5).background().color()
    )
    assert window.matrix_dimensions_label.text() == "Dimensions: 2 × 2"
    assert window.copy_matrix_button.isEnabled()

    window.copy_matrix_button.click()
    assert QApplication.clipboard().text() == "{{0,1},{1,0}}"

    window.matrix_type_combo.setCurrentIndex(
        window.matrix_type_combo.findData("degree")
    )
    window.matrix_button.click()
    assert window.matrix_preview.toPlainText() == "1 0\n0 1"
    assert window.matrix_dimensions_label.text() == "Dimensions: 2 × 2"

    window.matrix_type_combo.setCurrentIndex(
        window.matrix_type_combo.findData("ihara")
    )
    window.matrix_button.click()
    assert window.matrix_preview.matrix_shape == (4, 4)
    assert window.matrix_dimensions_label.text() == "Dimensions: 4 × 4"

    window.show()
    window.matrix_preview.setCurrentCell(0, 0)
    window.matrix_preview.setFocus()
    QApplication.clipboard().clear()
    QTest.keyClick(
        window.matrix_preview,
        Qt.Key.Key_C,
        Qt.KeyboardModifier.ControlModifier,
    )
    assert QApplication.clipboard().text() == "0"
    window.close()
