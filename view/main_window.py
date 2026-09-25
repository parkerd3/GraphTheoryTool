"""Main application window."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence, QPainter
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QCheckBox,
    QLabel,
    QListWidget,
    QMainWindow,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QGraphicsView,
    QWidget,
)

try:
    from ..model import Graph
    from .graph_scene import GraphScene
except ImportError:  # Supports launching with ``python main.py``.
    from model import Graph
    from view.graph_scene import GraphScene


class MainWindow(QMainWindow):
    """Initial two-panel application layout."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("GraphTheoryTool")
        self.resize(1100, 700)

        self.undo_action = QAction("Undo", self)
        self.undo_action.setShortcut(QKeySequence("Ctrl+Z"))
        self.undo_action.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        self.undo_action.triggered.connect(self.undo)
        self.addAction(self.undo_action)

        self.redo_action = QAction("Redo", self)
        self.redo_action.setShortcut(QKeySequence("Ctrl+Shift+Z"))
        self.redo_action.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        self.redo_action.triggered.connect(self.redo)
        self.addAction(self.redo_action)

        self.delete_action = QAction("Delete selection", self)
        self.delete_action.setShortcuts(
            [QKeySequence("Delete"), QKeySequence("Backspace")]
        )
        self.delete_action.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        self.delete_action.triggered.connect(self.delete_selected)
        self.addAction(self.delete_action)

        self.copy_action = QAction("Copy", self)
        self.copy_action.setShortcut(QKeySequence("Ctrl+C"))
        self.copy_action.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        self.copy_action.triggered.connect(self.copy_selected)
        self.addAction(self.copy_action)

        self.cut_action = QAction("Cut", self)
        self.cut_action.setShortcut(QKeySequence("Ctrl+X"))
        self.cut_action.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        self.cut_action.triggered.connect(self.cut_selected)
        self.addAction(self.cut_action)

        self.paste_action = QAction("Paste", self)
        self.paste_action.setShortcut(QKeySequence("Ctrl+V"))
        self.paste_action.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        self.paste_action.triggered.connect(self.paste_selected)
        self.addAction(self.paste_action)

        # Code involving creating the canvas on the right.
        self.graph = Graph()
        self.scene = GraphScene(self.graph, self)
        self.canvas = QGraphicsView(self.scene)
        self.canvas.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.canvas.setDragMode(QGraphicsView.DragMode.NoDrag)
        # AI explained the difference between the scene and the canvas;
        # essentially the scene is like the world, and the view is like
        # the camera. That way we can visually pan around and such w/o
        # messing with the actual location data of the graph object.

        toolbar = QWidget()
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)
        self.tool_buttons = {}

        tools = (
            ("pen", "✎", "Pen tool: add nodes and connect nodes"),
            ("eraser", "⌫", "Eraser tool: delete graph elements"),
            ("select", "↖", "Select tool: select and move graph elements"),
            ("hand", "✋", "Hand tool: pan the canvas"),
        )

        for mode, symbol, tooltip in tools:
            button = QToolButton()
            button.setText(symbol)
            button.setToolTip(tooltip)
            button.setCheckable(True)
            button.setAutoRaise(True)
            button.setFixedWidth(48)
            button.clicked.connect(
                lambda checked=False, selected_mode=mode: self.set_canvas_mode(
                    selected_mode
                )
            )
            self.tool_group.addButton(button)
            self.tool_buttons[mode] = button
            toolbar_layout.addWidget(button)

        history_controls = QWidget()
        history_layout = QHBoxLayout(history_controls)
        history_layout.setContentsMargins(0, 0, 0, 0)

        self.undo_button = QToolButton()
        self.undo_button.setText("Undo")
        self.undo_button.setToolTip("Undo the last graph edit (Ctrl+Z)")
        self.undo_button.setAutoRaise(True)
        self.undo_button.clicked.connect(self.undo)

        self.redo_button = QToolButton()
        self.redo_button.setText("Redo")
        self.redo_button.setToolTip("Redo the last undone graph edit (Ctrl+Shift+Z)")
        self.redo_button.setAutoRaise(True)
        self.redo_button.clicked.connect(self.redo)

        history_layout.addWidget(self.undo_button)
        history_layout.addWidget(self.redo_button)

        top_canvas_row = QWidget()
        top_canvas_layout = QHBoxLayout(top_canvas_row)
        top_canvas_layout.setContentsMargins(0, 0, 0, 0)
        top_canvas_layout.addStretch()
        top_canvas_layout.addWidget(toolbar)
        top_canvas_layout.addStretch()
        top_canvas_layout.addWidget(history_controls)

        self.canvas_container = QWidget()
        canvas_container_layout = QVBoxLayout(self.canvas_container)
        canvas_container_layout.setContentsMargins(0, 0, 0, 0)
        canvas_container_layout.addWidget(top_canvas_row)
        canvas_container_layout.addWidget(self.canvas)

        self.tool_buttons["pen"].setChecked(True)
        self.set_canvas_mode("pen")

        controls = QWidget()
        controls.setMinimumWidth(230)
        controls_layout = QVBoxLayout(controls)
        
        controls_layout.addWidget(QLabel("GraphTheoryTool"))
        controls_layout.addWidget(QLabel("The control panel will grow with the project."))

        self.matrix_button = QToolButton()
        self.matrix_button.setText("Generate matrix")
        self.show_labels_checkbox = QCheckBox("Show node labels")
        self.show_labels_checkbox.setChecked(False)
        self.show_labels_checkbox.toggled.connect(self.scene.set_labels_visible)
        controls_layout.addWidget(self.matrix_button)
        controls_layout.addWidget(self.show_labels_checkbox)
        # Now those buttons actually live where they should: in the left panel.



        controls_layout.addWidget(QLabel("Matrices"))
        controls_layout.addWidget(QListWidget())
        controls_layout.addStretch()

        # This adds that handy feature of being able to resize windows by dragging their borders.
        # This specific splitter lives between the left panel and the right canvas.
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(controls)
        splitter.addWidget(self.canvas_container)
        # Notice that the Controls panel and the Canvas are being *added to the splitter*, not vice versa.
        splitter.setStretchFactor(1, 1)

        # A QMainWindow object is special, so instead of adding all thos widgets
        # directly to it, we're going to add them all to one central widget.
        central_widget = QWidget()
        layout = QHBoxLayout(central_widget)
        # QHBoxLayout arranges its contents (soon to be the splitter) horizontally.
        layout.addWidget(splitter)
        self.setCentralWidget(central_widget)
        # That function comes from the parent class (QMainWindow). It basically
        # tells the main window to "use this widget as the main content area."

    def set_canvas_mode(self, mode: str) -> None:
        """Change the active canvas tool and configure basic view behavior."""

        self.scene.stop_erasing()
        self.scene.stop_moving_nodes()
        self.scene.cancel_selection_rectangle()
        if mode != "pen":
            self.scene.clear_selected_node()
        if mode != "select":
            self.scene.clear_selection()
        self.scene.mode = mode
        if mode == "hand":
            self.canvas.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        else:
            self.canvas.setDragMode(QGraphicsView.DragMode.NoDrag)

    def undo(self) -> None:
        """Undo the most recent graph edit."""

        self.scene.undo()

    def redo(self) -> None:
        """Redo the most recently undone graph edit."""

        self.scene.redo()

    def delete_selected(self) -> None:
        """Delete the currently selected nodes using the active history."""

        self.scene.delete_selection()

    def copy_selected(self) -> None:
        """Copy the current graph selection to the system clipboard."""

        self.scene.copy_selection()

    def cut_selected(self) -> None:
        """Copy the current graph selection, then delete it."""

        self.scene.cut_selection()

    def paste_selected(self) -> None:
        """Paste a graph fragment from the system clipboard."""

        self.scene.paste_selection()
