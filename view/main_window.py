"""Main application window."""

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QAction, QKeySequence, QPainter
from PySide6.QtWidgets import (
    QButtonGroup,
    QApplication,
    QComboBox,
    QHBoxLayout,
    QCheckBox,
    QLabel,
    QMainWindow,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QGraphicsView,
    QWidget,
)

try:
    from ..matrices import (
        adjacency_matrix,
        degree_matrix,
        ihara_matrix,
        laplacian_matrix,
        matrix_to_mathematica,
    )
    from ..model import Graph
    from .graph_scene import GraphScene
    from .matrix_preview import MatrixPreviewTable
except ImportError:  # Supports launching with ``python main.py``.
    from matrices import (
        adjacency_matrix,
        degree_matrix,
        ihara_matrix,
        laplacian_matrix,
        matrix_to_mathematica,
    )
    from model import Graph
    from view.graph_scene import GraphScene
    from view.matrix_preview import MatrixPreviewTable


class GraphCanvasView(QGraphicsView):
    """Canvas view that forwards no-button hover positions to the scene."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.viewport().setMouseTracking(True)
        self.viewport().installEventFilter(self)

    def eventFilter(self, watched, event) -> bool:
        if watched is self.viewport() and event.type() == QEvent.Type.MouseMove:
            scene = self.scene()
            if isinstance(scene, GraphScene):
                scene.handle_hover_position(
                    self.mapToScene(event.position().toPoint()),
                    event.modifiers(),
                    event.buttons(),
                )
        elif watched is self.viewport() and event.type() in (
            QEvent.Type.KeyPress,
            QEvent.Type.KeyRelease,
        ):
            scene = self.scene()
            if isinstance(scene, GraphScene) and event.key() in (
                Qt.Key.Key_Shift,
                Qt.Key.Key_Escape,
            ):
                if event.key() == Qt.Key.Key_Escape:
                    scene.cancel_shift_creation_preview()
                else:
                    scene.handle_modifier_change(event.modifiers())
        return super().eventFilter(watched, event)

    def mouseMoveEvent(self, event) -> None:
        scene = self.scene()
        if isinstance(scene, GraphScene):
            scene.handle_hover_position(
                self.mapToScene(event.position().toPoint()),
                event.modifiers(),
                event.buttons(),
            )
        super().mouseMoveEvent(event)

    def keyPressEvent(self, event) -> None:
        scene = self.scene()
        if isinstance(scene, GraphScene):
            if event.key() == Qt.Key.Key_Escape:
                scene.cancel_shift_creation_preview()
            elif event.key() == Qt.Key.Key_Shift:
                scene.handle_modifier_change(event.modifiers())
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event) -> None:
        scene = self.scene()
        if isinstance(scene, GraphScene) and event.key() == Qt.Key.Key_Shift:
            scene.handle_modifier_change(event.modifiers())
        super().keyReleaseEvent(event)


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

        self.select_all_action = QAction("Select all", self)
        self.select_all_action.setShortcut(QKeySequence("Ctrl+A"))
        self.select_all_action.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        self.select_all_action.triggered.connect(self.select_all)
        self.addAction(self.select_all_action)

        # Code involving creating the canvas on the right.
        self.graph = Graph()
        self.scene = GraphScene(self.graph, self)
        self.canvas = GraphCanvasView(self.scene)
        self.canvas.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.canvas.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.canvas.setMouseTracking(True)
        self.canvas.viewport().setMouseTracking(True)
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
            (
                "select",
                "↖",
                "Edit tool: select, move, create nodes, and connect nodes",
            ),
            ("eraser", "⌫", "Eraser tool: delete graph elements"),
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

        self.tool_buttons["select"].setChecked(True)
        self.set_canvas_mode("select")

        controls = QWidget()
        controls.setMinimumWidth(230)
        controls_layout = QVBoxLayout(controls)
        
        controls_layout.addWidget(QLabel("GraphTheoryTool"))
        controls_layout.addWidget(QLabel("The control panel will grow with the project."))

        self.matrix_button = QToolButton()
        self.matrix_button.setText("Generate matrix")
        self.matrix_button.clicked.connect(self.generate_matrix)

        self.matrix_type_combo = QComboBox()
        self.matrix_type_combo.addItem("Adjacency matrix", "adjacency")
        self.matrix_type_combo.addItem("Degree matrix", "degree")
        self.matrix_type_combo.addItem("Laplacian matrix", "laplacian")
        self.matrix_type_combo.addItem("Ihara matrix", "ihara")
        self._matrix_generators = {
            "adjacency": adjacency_matrix,
            "degree": degree_matrix,
            "laplacian": laplacian_matrix,
            "ihara": ihara_matrix,
        }

        self.matrix_dimensions_label = QLabel("Dimensions: —")
        self.matrix_preview = MatrixPreviewTable()

        self.copy_matrix_button = QToolButton()
        self.copy_matrix_button.setText("Copy matrix")
        self.copy_matrix_button.setToolTip(
            "Copy the complete matrix as a Mathematica-compatible list"
        )
        self.copy_matrix_button.setEnabled(False)
        self.copy_matrix_button.clicked.connect(self.copy_matrix)

        self._matrix_copy_text = ""

        self.show_labels_checkbox = QCheckBox("Show node labels")
        self.show_labels_checkbox.setChecked(False)
        self.show_labels_checkbox.toggled.connect(self.scene.set_labels_visible)
        controls_layout.addWidget(QLabel("Matrices"))
        controls_layout.addWidget(self.matrix_type_combo)
        controls_layout.addWidget(self.matrix_button)
        controls_layout.addWidget(self.matrix_dimensions_label)
        controls_layout.addWidget(self.matrix_preview, 1)
        controls_layout.addWidget(self.copy_matrix_button)
        controls_layout.addWidget(self.show_labels_checkbox)
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
        self.scene.cancel_shift_creation_preview()
        self.scene.cancel_selection_rectangle()
        self.scene.cancel_rotation_drag()
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

    def select_all(self) -> None:
        """Select every node and eligible edge in the graph."""

        self.scene.select_all()

    def generate_matrix(self) -> None:
        """Generate and display the matrix selected in the left panel."""

        matrix_type = self.matrix_type_combo.currentData()
        generator = self._matrix_generators.get(matrix_type)
        if generator is None:
            return

        matrix = generator(self.graph)
        self.matrix_preview.set_matrix(matrix)
        rows, columns = matrix.shape
        self.matrix_dimensions_label.setText(
            f"Dimensions: {rows} × {columns}"
        )
        self._matrix_copy_text = matrix_to_mathematica(matrix)
        self.copy_matrix_button.setEnabled(True)

    def copy_matrix(self) -> None:
        """Copy the complete generated matrix in Mathematica syntax."""

        if self._matrix_copy_text:
            QApplication.clipboard().setText(self._matrix_copy_text)
