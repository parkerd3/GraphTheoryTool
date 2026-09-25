"""Main application window."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
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

        self.canvas_container = QWidget()
        canvas_container_layout = QVBoxLayout(self.canvas_container)
        canvas_container_layout.setContentsMargins(0, 0, 0, 0)
        canvas_container_layout.addWidget(toolbar)
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

        if mode != "pen":
            self.scene.clear_selected_node()
        self.scene.mode = mode
        if mode == "hand":
            self.canvas.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        else:
            self.canvas.setDragMode(QGraphicsView.DragMode.NoDrag)
