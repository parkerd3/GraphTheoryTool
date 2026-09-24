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
