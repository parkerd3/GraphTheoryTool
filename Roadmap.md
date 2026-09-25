# Graph Matrix Tool Roadmap

This is an excellent project, and it’s large enough to teach you several valuable areas at once: GUI design, event handling, geometry, data modeling, file persistence, and linear algebra.

I recommend building it incrementally in Python with:

- **PySide6** for the GUI and interactive canvas
- **NumPy** for numerical matrices
- **NetworkX** for graph algorithms and validation
- **JSON** for saving and loading graphs

PySide6 is a good fit because its `QGraphicsView` system already supports movable objects, selection, zooming, and custom drawing.

## Proposed architecture

Keep three parts separate:

1. **Graph model**  
   Stores nodes, edges, labels, positions, and graph settings.

2. **Graph editor/view**  
   Displays the model and handles mouse interaction.

3. **Matrix engine**  
   Converts the graph model into adjacency, Laplacian, incidence, and other matrices.

This separation is important. The canvas should not be responsible for calculating matrices, and the matrix panel should not need to know how the graph was drawn.

## Roadmap

### Phase 1: Minimal graph model

Create classes representing:

- `Node`
  - internal ID
  - display number
  - `(x, y)` position

- `Edge`
  - starting node
  - ending node
  - directed/undirected status
  - optional weight

- `Graph`
  - collection of nodes
  - collection of edges
  - methods for adding, deleting, and querying them

At this stage, we can test the graph entirely from Python without a GUI.

One important design choice: nodes should have stable internal IDs separate from their visible numbers. If node 3 is deleted, we can decide whether later nodes are renumbered visually without corrupting the graph’s internal data.

### Phase 2: Basic GUI and graph creation

Build a window with:

- left control panel
- right graph canvas
- “Add node” mode
- “Add edge” mode
- node selection
- node movement
- edge drawing

The first usable milestone should be:

> Click the canvas to create nodes, click two nodes to connect them, and drag nodes around.

Everything else can wait until this works reliably.

### Phase 3: Editing tools

Add:

- delete node
- delete edge
- selection rectangle
- multi-node movement
- duplicate selection
- undo/redo
- keyboard shortcuts
- node-number visibility toggle

For transformations:

- translation
- rotation about the selection’s center
- reflection across a horizontal or vertical axis
- duplication with an offset

These should modify node coordinates in the model, not manually reposition graphics only.

### Phase 4: Zooming and navigation

Add:

- mouse-wheel zoom
- canvas panning
- “fit graph to window”
- optional grid
- optional snap-to-grid
- reset zoom

The graph should store positions in logical coordinates so zooming does not change the actual graph geometry.

### Phase 5: Saving and loading

Use a readable JSON format, for example:

```json
{
  "directed": false,
  "weighted": false,
  "nodes": [
    {"id": 0, "label": 1, "x": 120, "y": 200}
  ],
  "edges": [
    {"source": 0, "target": 1, "weight": 1}
  ]
}
```

Later, this can support graph metadata, colors, line styles, and other settings.

### Phase 6: Matrix generation

Start with the simplest matrices:

1. adjacency matrix
2. degree matrix
3. Laplacian matrix
4. signless Laplacian
5. incidence matrix
6. distance matrix

Then add:

- directed adjacency matrices
- weighted matrices
- transition matrices
- non-backtracking matrix
- oriented incidence matrices

The matrix engine should return a structured matrix object that can be displayed, copied, exported, or passed to other tools.

We will need to explicitly define how the program handles:

- directed edges
- loops
- multiple edges
- edge weights
- disconnected graphs
- isolated vertices

Those choices affect the matrix definitions.

### Phase 7: Matrix interface

The left panel can include:

- matrix-type selector
- small preview
- dimensions
- “Show full matrix” button
- copy-to-clipboard button
- selectable text display
- export as `.txt`, `.csv`, or perhaps Mathematica-compatible syntax

A useful layout would be:

```text
[Graph controls]

Matrices
[Adjacency ▼]
[Generate]

Preview:
  0 1 0
  1 0 1
  0 1 0

[Show full matrix] [Copy matrix]
```

The full matrix could appear either in a dialog or temporarily replace the graph canvas.

## Suggested project structure

```text
graph_matrix_tool/
├── main.py
├── model/
│   ├── graph.py
│   ├── node.py
│   └── edge.py
├── view/
│   ├── main_window.py
│   ├── graph_scene.py
│   └── graph_items.py
├── matrices/
│   ├── adjacency.py
│   ├── laplacian.py
│   └── nonbacktracking.py
├── storage/
│   └── json_io.py
└── tests/
    ├── test_graph.py
    └── test_matrices.py
```

We should not begin by implementing every feature. The safest first milestone is a tiny vertical slice:

> Open a window → create nodes → connect nodes → move nodes → generate an adjacency matrix.

Once that works, every later feature has a stable foundation.

I suggest we begin by designing the graph data model and building the smallest PySide6 window around it.

## Selection Tool Plan

The selection tool will be implemented in small, testable layers. The central
rule is that selection state belongs to the editor, not to the mathematical
`Graph` object:

```text
selected_nodes: set of internal node IDs
selected_edges: set of undirected edge keys
```

The graph model will continue to store graph facts. The scene will coordinate
selection, and graphics items will display selected state.

### Selection invariants

- An edge may be selected only when both endpoint nodes are selected.
- Selecting a node automatically selects edges joining it to already-selected
  nodes.
- Deselecting a node automatically deselects every incident edge.
- Ctrl-click toggles an individual node or an eligible edge.
- Clicking blank canvas without Ctrl clears the entire selection.
- A rectangle selects nodes using a small adjustable hitbox around each node
  center rather than requiring the entire circle to be inside the rectangle.
- Rectangle selection derives edge selection from the endpoint rule above.

### Implementation checklist

#### Stage 0: Prepare the graphics layer

- [x] Introduce `NodeGraphicsItem` and `EdgeGraphicsItem` classes.
- [x] Give each graphics item a reliable reference to its model ID or edge key.
- [x] Centralize normal, selected, and hover appearance in `graph_items.py`.
- [x] Add focused tests for the selection data structures before adding complex
      mouse behavior.

#### Stage 1: Single-element selection

- [x] Add `selected_nodes` and `selected_edges` to `GraphScene`.
- [x] Select one node with a normal left click.
- [x] Make selected nodes solid orange.
- [x] Clear the selection by clicking blank canvas.
- [x] Make Ctrl-click add or remove a node.
- [x] Keep edge selection synchronized with the endpoint invariants.

#### Stage 2: Edge selection

- [x] Give selected edges a solid orange pen.
- [x] Allow an edge to be selected only when both endpoints are selected.
- [x] Allow Ctrl-click to toggle an eligible edge.
- [x] Ensure deselecting either endpoint removes the edge from the selection.
- [x] Ensure clicking an ineligible edge cannot add it to the selection.

#### Stage 3: Rectangle selection

- [x] Start a selection rectangle from blank canvas in Select mode.
- [x] Draw the rectangle while the mouse is held.
- [x] On release, select nodes whose small center hitboxes fit inside the rectangle.
- [x] Support Ctrl-drag to add to or subtract from the existing selection.
- [x] Recompute automatic edge selection after the rectangle is applied.

#### Stage 3.5: Undo and redo

- [x] Add serializable graph snapshots.
- [x] Add bounded undo and redo stacks.
- [x] Record node and edge creation as graph edits.
- [x] Record node and edge deletion as graph edits.
- [x] Group an eraser drag into one history entry.
- [x] Restore the scene graphics after undoing or redoing.
- [x] Add `Ctrl+Z` and `Ctrl+Shift+Z` shortcuts.
- [x] Add visible Undo and Redo controls beside the canvas toolbar.
- [ ] Add history grouping for node and group movement.
- [x] Add history support for cut and paste; transformations remain for Stage 7.

#### Stage 4: Keyboard deletion

- [x] Handle `Delete` and `Backspace` in the scene or main window.
- [x] Provide edge-only deletion without deleting endpoint nodes.
- [x] Delete selected nodes and all incident edges.
- [x] Renumber visible node labels and refresh their graphics.
- [x] Clear selection entries for deleted objects.

#### Stage 5: Moving nodes and groups

- [x] Make selected nodes draggable in Select mode.
- [x] Move every selected node by the same scene-coordinate delta.
- [x] Update model positions when a drag ends or changes.
- [x] Update connected edge lines continuously while nodes move.
- [x] Keep edges attached to stationary nodes stretched correctly.
- [x] Preserve the selection after the move is complete.

#### Stage 6: Copy, cut, and paste

- [x] Define the clipboard payload for selected nodes and eligible selected edges.
- [x] Implement `Ctrl+C` using a self-contained graph fragment format.
- [x] Implement `Ctrl+X` as copy followed by deletion.
- [x] Implement `Ctrl+V` with fresh internal IDs and an offset from the source.
- [x] Deselect the old selection after pasting.
- [x] Select all newly pasted nodes and edges.
- [x] Add a `paste_nodes_only()` operation; expose it through the Stage 7 context menu.
- [x] Ensure copied edges are recreated only when both endpoint nodes are in the
      pasted fragment and the edge was selected.

#### Stage 7: Context menus and transformations

- [x] Add a right-click context menu for selected elements.
- [x] Add “deselect all edges.”
- [x] Add “delete selected edges.”
- [x] Add “delete all connected edges.”
- [ ] Add horizontal and vertical reflection.
- [ ] Preserve every edge attached to reflected nodes, including edges outside
      the selection.
- [x] Add hover-activated rotation controls for multi-node selections, with a
      dashed guide circle and draggable handle.
- [x] Keep rotation as one undoable edit and update connected edges live.
- [ ] Add other transformations after reflection is reliable.

#### Stage 8: Interaction polish

- [ ] Add a Ctrl-hover orange outline for objects that would be selectable.
- [ ] Tune the node selection hitbox and rectangle margin.
- [ ] Make right-click behavior predictable when clicking selected versus
      unselected elements.
- [ ] Add undo/redo for selection-dependent edits.
- [ ] Add automated tests for each selection invariant and editing command.

### Recommended next milestone

The next implementation should be Stage 7: add context menus and begin the
transformation tools. The selection invariants, rectangle selection, keyboard
deletion, movement, undo/redo, and clipboard operations are now in place.
