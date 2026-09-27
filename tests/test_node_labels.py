import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from GraphTheoryTool.view.graph_scene import GraphScene


def get_qapplication() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_node_labels_are_bold_and_slightly_larger() -> None:
    get_qapplication()
    scene = GraphScene()
    node = scene.graph.add_node(100, 100)
    scene.add_node_visual(node)

    label = scene.node_items[node.id]["label"]

    assert label.font().bold()
    assert label.font().pointSize() >= 10
