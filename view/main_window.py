"""Main application window."""

from pathlib import Path

from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtGui import QAction, QIcon, QKeySequence, QPainter
from PySide6.QtWidgets import (
    QButtonGroup,
    QApplication,
    QComboBox,
    QHBoxLayout,
    QCheckBox,
    QLabel,
    QMainWindow,
    QRadioButton,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QGraphicsView,
    QGraphicsOpacityEffect,
    QWidget,
)

try:
    from ..matrices import (
        adjacency_matrix,
        degree_matrix,
        directed_arcs,
        ihara_matrix,
        laplacian_matrix,
        matrix_to_mathematica,
        matrix_to_python,
        nonbacktracking_matrix,
    )
    from ..model import Graph
    from .graph_scene import GraphScene
    from .arc_scene import DirectedArcScene
    from .matrix_preview import MatrixPreviewTable
except ImportError:  # Supports launching with ``python main.py``.
    from matrices import (
        adjacency_matrix,
        degree_matrix,
        directed_arcs,
        ihara_matrix,
        laplacian_matrix,
        matrix_to_mathematica,
        matrix_to_python,
        nonbacktracking_matrix,
    )
    from model import Graph
    from view.graph_scene import GraphScene
    from view.arc_scene import DirectedArcScene
    from view.matrix_preview import MatrixPreviewTable


class GraphCanvasView(QGraphicsView):
    """Canvas view that forwards no-button hover positions to the scene."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.creation_controls: QWidget | None = None
        self._overlay_controls: dict[str, QWidget] = {}
        self._overlay_widgets: set[QWidget] = set()
        self.viewport().setMouseTracking(True)
        self.viewport().installEventFilter(self)
        self.creation_hint = QLabel("Hold Shift to create", self.viewport())
        self.creation_hint.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.creation_hint.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        hint_font = self.creation_hint.font()
        hint_font.setPointSize(max(12, hint_font.pointSize() + 2))
        self.creation_hint.setFont(hint_font)
        opacity = QGraphicsOpacityEffect(self.creation_hint)
        opacity.setOpacity(0.4)
        self.creation_hint.setGraphicsEffect(opacity)
        if self.scene() is not None:
            self.scene().changed.connect(self._update_creation_hint)
        self._update_creation_hint()
        self._position_canvas_controls()

    def setScene(self, scene) -> None:
        """Keep the empty-canvas hint in sync when switching canvas scenes."""

        if hasattr(self, "creation_hint") and self.scene() is not None:
            self.scene().changed.disconnect(self._update_creation_hint)
        super().setScene(scene)
        if hasattr(self, "creation_hint"):
            if scene is not None:
                scene.changed.connect(self._update_creation_hint)
            self._update_creation_hint()

    def _update_creation_hint(self) -> None:
        """Only editable, truly empty graphs need the creation prompt."""

        scene = self.scene()
        self.creation_hint.setVisible(
            isinstance(scene, GraphScene) and len(scene.graph) == 0
        )

    def set_creation_controls(self, controls: QWidget) -> None:
        """Anchor a widget to the viewport's lower-left corner during panning."""

        self.creation_controls = controls
        self.add_overlay_controls(controls, "bottom-left")

    def add_overlay_controls(self, controls: QWidget, anchor: str) -> None:
        """Place native controls over the canvas without adding scene items."""

        self._overlay_controls[anchor] = controls
        controls.setParent(self.viewport())
        for widget in (controls, *controls.findChildren(QWidget)):
            widget.installEventFilter(self)
            self._overlay_widgets.add(widget)
        self._position_canvas_controls()

    def _position_canvas_controls(self) -> None:
        overlays = getattr(self, "_overlay_controls", {})
        for anchor, controls in overlays.items():
            controls.adjustSize()
            if anchor == "top-center":
                x = (self.viewport().width() - controls.width()) // 2
            elif anchor == "top-right":
                x = self.viewport().width() - controls.width() - 10
            else:
                x = 10
            y = (
                self.viewport().height() - controls.height() - 10
                if anchor == "bottom-left" else 10
            )
            controls.move(max(10, x), max(10, y))
            controls.raise_()

        hint = getattr(self, "creation_hint", None)
        if hint is not None:
            hint.adjustSize()
            hint.move(
                (self.viewport().width() - hint.width()) // 2,
                (self.viewport().height() - hint.height()) // 2,
            )

        if all(anchor in overlays for anchor in ("top-left", "top-center", "top-right")):
            # Leave room for the centered tools and both corner panels, even
            # when the sidebar grows or the window is narrowed.
            corner_width = max(overlays["top-left"].width(), overlays["top-right"].width())
            viewport_width = overlays["top-center"].width() + 2 * corner_width + 40
            self.setMinimumWidth(
                viewport_width + 2 * self.frameWidth() + self.verticalScrollBar().sizeHint().width()
            )

    def scrollContentsBy(self, dx: int, dy: int) -> None:
        super().scrollContentsBy(dx, dy)
        # QGraphicsView scrolls viewport children too; restore the overlay's
        # screen position after moving the scene contents.
        self._position_canvas_controls()

    def eventFilter(self, watched, event) -> bool:
        if watched is self.viewport() and event.type() == QEvent.Type.Resize:
            self._position_canvas_controls()
        elif (
            watched in self._overlay_widgets and event.type() == QEvent.Type.Enter
        ) or (
            watched is self.viewport() and event.type() == QEvent.Type.Leave
        ):
            scene = self.scene()
            if isinstance(scene, GraphScene):
                scene.cancel_shift_creation_preview()
                scene.last_cursor_position = None
        elif watched in self._overlay_widgets and event.type() == QEvent.Type.ContextMenu:
            return True
        elif (
            watched in self._overlay_widgets
            and event.type() in (
                QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease,
                QEvent.Type.MouseButtonDblClick,
            )
            and (watched in self._overlay_controls.values() or not watched.isEnabled())
        ):
            # Empty panel margins and disabled controls must not send clicks
            # through to the graph underneath.
            return True
        elif watched is self.viewport() and event.type() == QEvent.Type.MouseMove:
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
        self.arc_scene = DirectedArcScene(self.graph, self)
        self.arc_view_active = False
        self.canvas = GraphCanvasView(self.scene)
        self.canvas.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.canvas.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.canvas.setMouseTracking(True)
        self.canvas.viewport().setMouseTracking(True)

        self.creation_controls = QWidget()
        self.creation_controls.setAutoFillBackground(True)
        creation_layout = QHBoxLayout(self.creation_controls)
        creation_layout.setContentsMargins(4, 4, 4, 4)
        creation_layout.setSpacing(4)
        self.creation_mode_group = QButtonGroup(self)
        self.creation_mode_group.setExclusive(True)
        self.creation_mode_buttons: dict[str, QToolButton] = {}
        creation_modes = (
            ("loop", "Loop", "Shift-click: connect, then select only the target node"),
            ("web", "Web", "Shift-click: connect, then add the target to the selection"),
            ("points", "Points", "Shift-click: connect, then deselect all nodes"),
            ("append", "Append", "Shift-click: connect while keeping the previous selection"),
        )
        for creation_mode, label, tooltip in creation_modes:
            button = QToolButton()
            button.setText(label)
            button.setIcon(QIcon(str(Path(__file__).with_name("icons") / f"creation-{creation_mode}.svg")))
            button.setIconSize(QSize(40, 40))
            button.setFixedSize(48, 48)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            button.setAccessibleName(f"{label} creation mode")
            button.setToolTip(f"{label}: {tooltip}")
            button.setCheckable(True)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.clicked.connect(
                lambda checked=False, chosen_mode=creation_mode: self.set_creation_mode(
                    chosen_mode
                )
            )
            self.creation_mode_group.addButton(button)
            self.creation_mode_buttons[creation_mode] = button
            creation_layout.addWidget(button)
        self.creation_mode_buttons[self.scene.creation_mode].setChecked(True)
        self.canvas.set_creation_controls(self.creation_controls)
        # AI explained the difference between the scene and the canvas;
        # essentially the scene is like the world, and the view is like
        # the camera. That way we can visually pan around and such w/o
        # messing with the actual location data of the graph object.

        self.tool_controls = QWidget()
        self.tool_controls.setAutoFillBackground(True)
        toolbar_layout = QHBoxLayout(self.tool_controls)
        toolbar_layout.setContentsMargins(4, 4, 4, 4)
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
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.clicked.connect(
                lambda checked=False, selected_mode=mode: self.set_canvas_mode(
                    selected_mode
                )
            )
            self.tool_group.addButton(button)
            self.tool_buttons[mode] = button
            toolbar_layout.addWidget(button)

        self.history_controls = QWidget()
        self.history_controls.setAutoFillBackground(True)
        history_layout = QHBoxLayout(self.history_controls)
        history_layout.setContentsMargins(4, 4, 4, 4)

        self.undo_button = QToolButton()
        self.undo_button.setText("Undo")
        self.undo_button.setToolTip("Undo the last graph edit (Ctrl+Z)")
        self.undo_button.setAutoRaise(True)
        self.undo_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.undo_button.clicked.connect(self.undo)

        self.redo_button = QToolButton()
        self.redo_button.setText("Redo")
        self.redo_button.setToolTip("Redo the last undone graph edit (Ctrl+Shift+Z)")
        self.redo_button.setAutoRaise(True)
        self.redo_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.redo_button.clicked.connect(self.redo)

        history_layout.addWidget(self.undo_button)
        history_layout.addWidget(self.redo_button)

        self.label_controls = QWidget()
        self.label_controls.setAutoFillBackground(True)
        label_layout = QHBoxLayout(self.label_controls)
        label_layout.setContentsMargins(4, 4, 4, 4)
        self.show_labels_checkbox = QCheckBox("Show Labels")
        self.show_labels_checkbox.setToolTip("Show or hide node labels")
        self.show_labels_checkbox.setChecked(False)
        self.show_labels_checkbox.toggled.connect(self.scene.set_labels_visible)
        self.show_labels_checkbox.clicked.connect(lambda checked=False: self.canvas.setFocus())
        label_layout.addWidget(self.show_labels_checkbox)

        self.canvas.add_overlay_controls(self.tool_controls, "top-center")
        self.canvas.add_overlay_controls(self.history_controls, "top-right")
        self.canvas.add_overlay_controls(self.label_controls, "top-left")

        self.canvas_container = QWidget()
        canvas_container_layout = QVBoxLayout(self.canvas_container)
        canvas_container_layout.setContentsMargins(0, 0, 0, 0)
        canvas_container_layout.addWidget(self.canvas)

        self.tool_buttons["select"].setChecked(True)
        self.set_canvas_mode("select")

        controls = QWidget()
        controls.setMinimumWidth(230)
        controls_layout = QVBoxLayout(controls)

        self.matrix_button = QToolButton()
        self.matrix_button.setText("Generate matrix")
        self.matrix_button.clicked.connect(self.generate_matrix)

        self.matrix_type_combo = QComboBox()
        self.matrix_type_combo.addItem("Adjacency matrix", "adjacency")
        self.matrix_type_combo.addItem("Degree matrix", "degree")
        self.matrix_type_combo.addItem("Laplacian matrix", "laplacian")
        self.matrix_type_combo.addItem("Ihara matrix", "ihara")
        self.matrix_type_combo.addItem("Non-backtracking matrix", "nonbacktracking")
        self._matrix_generators = {
            "adjacency": adjacency_matrix,
            "degree": degree_matrix,
            "laplacian": laplacian_matrix,
            "ihara": ihara_matrix,
            "nonbacktracking": nonbacktracking_matrix,
        }

        self.matrix_dimensions_label = QLabel("Dimensions: —")
        self.matrix_preview = MatrixPreviewTable()

        self.copy_matrix_button = QToolButton()
        self.copy_matrix_button.setText("Copy matrix")
        self.copy_matrix_button.setToolTip(
            "Copy the complete matrix using the selected list syntax"
        )
        self.copy_matrix_button.setEnabled(False)
        self.copy_matrix_button.clicked.connect(self.copy_matrix)

        self.matrix_copy_format_group = QButtonGroup(self)
        self.matrix_copy_format_group.setExclusive(True)
        self.mathematica_radio = QRadioButton("Mathematica")
        self.python_radio = QRadioButton("Python")
        self.mathematica_radio.setToolTip("Copy a nested list using curly braces")
        self.python_radio.setToolTip("Copy a nested list using square brackets")
        self.matrix_copy_format_group.addButton(self.mathematica_radio)
        self.matrix_copy_format_group.addButton(self.python_radio)
        self.mathematica_radio.setChecked(True)
        copy_layout = QHBoxLayout()
        copy_layout.addWidget(self.copy_matrix_button)
        copy_layout.addWidget(self.mathematica_radio)
        copy_layout.addWidget(self.python_radio)
        copy_layout.addStretch()

        self._matrix_copy_texts: dict[str, str] = {}

        self.show_arc_view_checkbox = QCheckBox("Show directed arc view")
        self.show_arc_view_checkbox.setToolTip(
            "Inspect numbered arcs matching the non-backtracking matrix headers"
        )
        self.show_arc_view_checkbox.toggled.connect(self.set_arc_view)
        self.matrix_type_combo.currentIndexChanged.connect(
            self._update_arc_view_availability
        )
        self._update_arc_view_availability()

        controls_layout.addWidget(QLabel("View"))
        controls_layout.addWidget(self.show_arc_view_checkbox)
        controls_layout.addWidget(QLabel("Matrices"))
        controls_layout.addWidget(self.matrix_type_combo)
        controls_layout.addWidget(self.matrix_button)
        controls_layout.addLayout(copy_layout)
        controls_layout.addWidget(self.matrix_dimensions_label)
        controls_layout.addWidget(self.matrix_preview, 1)

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

        if self.arc_view_active:
            return

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
        self._update_creation_controls_availability()

    def set_creation_mode(self, mode: str) -> None:
        """Switch Shift-click behavior without changing the current selection."""

        if self.arc_view_active or self.scene.mode != "select":
            return
        self.scene.set_creation_mode(mode)
        self.creation_mode_buttons[mode].setChecked(True)
        self.canvas.setFocus()

    def _update_creation_controls_availability(self) -> None:
        self.creation_controls.setEnabled(
            self.scene.mode == "select" and not self.arc_view_active
        )

    def _update_arc_view_availability(self) -> None:
        """Allow the derived arc view only for non-backtracking matrices."""

        available = self.matrix_type_combo.currentData() == "nonbacktracking"
        if not available:
            self.show_arc_view_checkbox.setChecked(False)
        self.show_arc_view_checkbox.setEnabled(available)

    def set_arc_view(self, visible: bool) -> None:
        """Switch the canvas between graph editing and arc inspection."""

        visible = visible and (
            self.matrix_type_combo.currentData() == "nonbacktracking"
        )
        self.scene.stop_erasing()
        self.scene.stop_moving_nodes()
        self.scene.cancel_shift_creation_preview()
        self.scene.cancel_selection_rectangle()
        self.scene.cancel_rotation_drag()
        self.arc_view_active = visible

        if visible:
            self.arc_scene.rebuild_from_graph()
            self.arc_scene.setSceneRect(self.scene.sceneRect())
            self.canvas.setScene(self.arc_scene)
            self.canvas.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.tool_buttons["hand"].setChecked(True)
            # Refresh the matrix with the exact same arc numbering as the view.
            self.generate_matrix()
        else:
            self.canvas.setScene(self.scene)
            self.tool_buttons[self.scene.mode].setChecked(True)
            self.canvas.setDragMode(
                QGraphicsView.DragMode.ScrollHandDrag
                if self.scene.mode == "hand"
                else QGraphicsView.DragMode.NoDrag
            )

        self.show_labels_checkbox.setEnabled(not visible)
        self.tool_buttons["select"].setEnabled(not visible)
        self.tool_buttons["eraser"].setEnabled(not visible)
        for action in (
            self.undo_action,
            self.redo_action,
            self.delete_action,
            self.copy_action,
            self.cut_action,
            self.paste_action,
            self.select_all_action,
        ):
            action.setEnabled(not visible)
        self.undo_button.setEnabled(not visible)
        self.redo_button.setEnabled(not visible)
        self._update_creation_controls_availability()

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
        self._matrix_copy_texts = {
            "mathematica": matrix_to_mathematica(matrix),
            "python": matrix_to_python(matrix),
        }
        self.copy_matrix_button.setEnabled(True)
        if matrix_type == "nonbacktracking":
            for index, arc in enumerate(directed_arcs(self.graph)):
                source = self.graph.get_node(arc.source).label
                target = self.graph.get_node(arc.target).label
                description = f"Arc {arc.index}: {source} → {target}"
                self.matrix_preview.horizontalHeaderItem(index).setToolTip(description)
                self.matrix_preview.verticalHeaderItem(index).setToolTip(description)

    def copy_matrix(self) -> None:
        """Copy the complete generated matrix using the selected syntax."""

        syntax = "python" if self.python_radio.isChecked() else "mathematica"
        text = self._matrix_copy_texts.get(syntax, "")
        if text:
            QApplication.clipboard().setText(text)
