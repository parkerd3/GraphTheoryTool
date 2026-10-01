# Codex Handoff

## 1. Objective

GraphTheoryTool is a PySide6 desktop editor for drawing **simple, unweighted,
undirected graphs** and generating graph matrices. The current matrix work
includes a non-backtracking (Hashimoto) matrix and a read-only visual mapping
from its rows/columns to directed edge-arcs.

**Verified:** The project root is
`C:\Users\Owner\Desktop\SCHOOL\CodingSht\PersonalGitHub\GraphTheoryTool`.
Do not use the obsolete `Coding Sht` path (with a space).

## 2. Current architecture relevant to this work

| Layer | Responsibility | Key files |
| --- | --- | --- |
| Model | Nodes have stable internal IDs, mutable positions, and visible labels. `Graph` enforces no self-loops or duplicate connections. | `model/graph.py`, `model/node.py`, `model/edge.py` |
| Editor scene | Owns Qt graphics and selection/editor state; updates the model and history. | `view/graph_scene.py`, `view/graph_items.py` |
| Window | Owns tools, keyboard actions, matrix controls, normal graph scene, and derived arc scene. | `view/main_window.py` |
| Matrix engine | Produces NumPy arrays and Mathematica-formatted copy text. | `matrices/` |
| Derived arc view | Builds display-only curved arrows from the graph; it never changes graph data. | `view/arc_scene.py` |
| Tests | Pytest tests for model, editor interactions, matrices, and arc view. | `tests/` |

`main.py` supports both `python main.py` and package imports through a relative-import fallback.

## 3. Requirements and constraints

### Verified facts

- The editor currently creates only simple undirected, unweighted edges.
- `Edge` and `Graph.add_edge()` have `directed` and `weight` fields for future
  work, but there is no editing UI for either.
- Non-backtracking arcs are derived in **edge creation order**. Each undirected
  edge contributes `(source, target)` followed immediately by its reverse.
- Arc indices are 1-based; matrix array indices remain 0-based.
- The non-backtracking matrix has one row and column per arc. Transition
  `u -> v` to `x -> y` is 1 exactly when `v == x` and `y != u`.
- The directed-arc canvas is inspection-only: edit, selection, clipboard,
  delete, undo, and redo actions are disabled; panning remains available.

### Decisions made

- Keep true directed/weighted graph authoring as a separate future feature.
- Do not store derived arcs in `Graph`; regenerate them from graph edges so the
  mathematical graph remains the single source of truth.
- Display both orientations of every undirected edge as curved arrows on
  opposite sides, labelled to match the non-backtracking matrix headers.
- Enable the arc-view checkbox only while the matrix selector is
  `Non-backtracking matrix`; changing away automatically restores the normal
  editor scene.

## 4. Work already completed

### Verified facts

- Editor supports Shift-based node/edge creation with previews, selection and
  rectangular selection, group movement, erasing, panning, copy/cut/paste,
  undo/redo, rotation, reflection, and `Ctrl+A`.
- Supported matrix choices are adjacency, degree, Laplacian, Ihara, and
  non-backtracking.
- `matrices/nonbacktracking.py` exposes `DirectedArc`, `directed_arcs(graph)`,
  and `nonbacktracking_matrix(graph)`; `matrices/__init__.py` re-exports them.
- `DirectedArcScene` displays numbered curved arrows with arrowheads and
  endpoint tooltips. Node labels are omitted in this view.
- `MainWindow` has a View section above Matrices. It contains Show node labels
  and Show directed arc view. Copy matrix is immediately below Generate matrix.
- Generating a non-backtracking matrix applies matching endpoint tooltips to
  its row and column headers. Other matrix displays clear those tooltips.
- The fixed-capacity matrix preview uses numeric headers and a dark 5-by-5
  checkerboard background.
- JSON save/load helpers exist in `storage/json_io.py`, but are not currently
  wired into the GUI.

## 5. Rejected approaches and why

### Decisions made

- **Making the graph itself directed for non-backtracking work:** rejected.
  The arcs are a derived representation of the existing undirected graph, not
  new editable edges.
- **Context-menu rotation:** replaced. Rotation is now controlled by the
  hover-activated guide/handle at the centre of a multi-node selection, which
  avoids repeated menu navigation.
- **Separate Add Node and Add Edge workflow:** replaced by the Select/Edit
  workflow with Shift gestures, so creating and manipulating a graph do not
  require constant tool switching.

## 6. Current known problems and limitations

### Verified limitations

- Directed and weighted edge editing is not implemented, despite model fields
  existing for them. The non-backtracking module explicitly notes that directed
  conventions will need refinement when that work begins.
- No GUI save/load controls, full-size matrix view/export controls, incidence
  matrix, or distance matrix are implemented.
- Self-loops and parallel edges are prohibited by `Graph.add_edge()`.
- History is snapshot-based and bounded to 100 entries. The roadmap still
  lists movement-history grouping as incomplete.

### Working-tree state to preserve

`git status --short` currently reports uncommitted work. The matrix/arc-view
files are part of the current feature and should not be discarded. `Ideas.md`
and the whitespace-only change in `model/graph.py` predate this feature and
should be treated as user changes unless the user directs otherwise.

Current changed/new files:

```text
M  Ideas.md
M  README.md
M  Roadmap.md
M  matrices/__init__.py
M  matrices/nonbacktracking.py
M  model/graph.py
M  tests/test_matrices.py
M  tests/test_matrix_interface.py
M  view/main_window.py
M  view/matrix_preview.py
?? tests/test_arc_view.py
?? view/arc_scene.py
?? docs/CODEX_HANDOFF.md
```

### Unresolved hypotheses

- A manual end-user pass may still reveal interaction or visual issues that
  automated Qt tests do not capture. There is no failing test or documented
  defect at handoff time.
- If directed-edge editing is added later, the desired convention for the
  non-backtracking matrix (and visual arc view) must be explicitly specified.

## 7. Validation status

### Verified

Run from the project root:

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider
```

Result at handoff: **53 passed in 0.61s**.

Relevant coverage includes:

- `tests/test_matrices.py`: directed-arc ordering, allowed path continuation,
  reversal rejection, isolated nodes, and no model mutation.
- `tests/test_arc_view.py`: checkbox gating, paired-arc geometry, read-only
  behavior, matrix/header correspondence, scene restoration, and rebuild after
  deletion.
- `tests/test_matrix_interface.py`: selector contents and matrix copy/preview.

## 8. Relevant files

- `main.py` — application entry point.
- `view/main_window.py` — sidebar, matrix selection, tool actions, scene swap.
- `view/graph_scene.py` — editor behavior and graph mutations.
- `view/arc_scene.py` — derived, read-only directed-arc rendering.
- `view/matrix_preview.py` — fixed-capacity matrix table and header cleanup.
- `matrices/nonbacktracking.py` — canonical arc ordering and Hashimoto matrix.
- `matrices/adjacency.py`, `matrices/laplacian.py`, `matrices/ihara.py` — other
  current matrix definitions.
- `model/graph.py` — graph invariants and serialization snapshots.
- `Roadmap.md` — completed editor/matrix milestones and remaining high-level
  matrix work.
- `README.md` — user-facing description of current behavior.

## 9. Exact recommended next steps

1. Open exactly the project root stated above and run `git status --short`;
   preserve all listed worktree changes. Do not use the obsolete path.
2. Run the validation command in section 7 before making changes.
3. If the user wants to continue matrix work, implement **one** next matrix
   type—incidence is the natural next choice—and first decide/document its
   orientation and loop/multiple-edge conventions before changing the model or
   UI.
4. If the user instead wants persistence, expose the existing JSON helpers
   through explicit save/load controls and add round-trip UI tests.
5. Before any directed/weighted editor work, get a concrete specification for
   visual representation, duplicate-edge rules, matrix conventions, and file
   compatibility. Do not infer those rules from the current derived arc view.
6. Do not commit, discard, or reformat the current working tree without the
   user's explicit instruction.
