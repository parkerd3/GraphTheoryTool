# GraphTheoryTool

I directed Codex to make this program as an aid for my university research
involving graphs and their various representative matrices. It is designed to
let you draw a graph visually, as you would on a piece of paper, and
automatically generate a matrix for it. I used Wolfram Mathematica in
conjunction with this project, so the program is built to let you copy the
generated matrix to the clipboard using Mathematica syntax.

The project is written in Python. The GUI is built with PySide6, and the matrix
capabilities are pretty much all handled with NumPy.

## Current status

The project is still pretty bare-bones, it currently only supports the
generation of adjacency, degree, laplacian-adjacency, non-backtracking matrices, and the Ihara
matrix which was central to the research project that this program was created
for.

So far, only simple graphs are supported (no weighted or one-directional edges
yet), however a lot of care has been taken to make the graph editor feel as
smooth and intuitive as possible.

## Features

### Graph editor

- Create nodes and edges with the Edit tool. Edit, Eraser, and Hand controls
  sit at the top-center of the canvas; Undo and Redo sit at the top-right.
- Hold `Shift` while hovering to preview a node or connecting edges.
- `Shift`-click the canvas to create a node.
- With nodes selected, `Shift`-click the canvas or another node to connect
  all selected nodes in one gesture.
- Choose the Shift-click mode using the graph pictograms in the canvas's
  lower-left corner; hover over a button to see its mode name. The same
  rule applies when creating a node or clicking an existing node, after all
  missing connections are created:

  - **Loop** (startup default): select only the target node, making chains and
    loops easy to draw.
  - **Web**: add the target to the existing selection.
  - **Points**: deselect all nodes, making subsequent clicks place isolated nodes.
  - **Append**: keep the previous selection without adding the target.
- Changing creation modes preserves the current selection. The mode is
  remembered when switching tools or returning from the directed arc view.
- Click on a node to select it, or click and drag to select multiple elements.
- Hold `Ctrl` to add or remove elements from the selection.
- Click and drag selected nodes to move them around the canvas.
- Click with the Eraser tool to delete individual nodes or edges, you can also
  click and drag over elements with the eraser to delete them.
- Move the canvas with the scrollbars on the sides, or with the hand tool.
- Check "Show Labels" at the top-left of the canvas to display/hide the numbers
  on the nodes.
- With "Non-backtracking matrix" selected, check "Show directed arc view" to
  inspect the two numbered directions of each edge. Node labels are hidden in
  this view, and panning is available while graph editing is disabled.
- Selected nodes can be transformed via reflection and rotation.
- Right-click selected nodes to bring up a context menu where you can do things
  such as deselect/delete all edges connected to the selected nodes, or create
  edges between every single selected node to every other selected node.

### Matrix generation

The matrix panel is organized into a grid that will display the number of each
row and column. The checkered pattern organizes entries into groups of 5x5 for
easier readability. 

After selecting the type of matrix from the drop-down menu, press the "Generate
Matrix" button to populate the grid. Next to "Copy matrix", select "Mathematica"
for curly-brace syntax or "Python" for square-bracket syntax. The button copies
the generated matrix as a nested list in the selected format. Mathematica is
selected by default, and switching formats does not require regenerating the matrix.

The matrix panel currently supports:

- Adjacency matrices
- Degree matrices
- Laplacian-adjacency matrices
- Ihara matrices
- Non-backtracking matrices

For a graph with `m` undirected edges, the non-backtracking matrix has `2m`
rows and columns, one per directed arc. An entry is 1 when the row arc can be
followed by the column arc without immediately reversing direction. The arc
numbers in the canvas match the matrix headers; hover over an arc or a header
to see its source and target nodes. Turning on the arc view generates the
matrix with the current arc numbering. Switching to another matrix type
automatically returns to the graph editor.

The Ihara matrix uses the block definition:

```text
K = {{A, D - I},
     {-I, 0}}
```

where `A` is the adjacency matrix, `D` is the degree matrix, and `I` is the
identity matrix.

## Keyboard shortcuts

| Shortcut | Action |
| --- | --- |
| `Ctrl+A` | Select all nodes and eligible edges |
| `Ctrl+C` | (Canvas) Copy the selected graph fragment|
| `Ctrl+X` | Cut the selected graph fragment |
| `Ctrl+V` | Paste a copied graph fragment |
| `Ctrl+Z` | Undo |
| `Ctrl+Shift+Z` | Redo |
| `Delete` / `Backspace` | Delete the current selection |
| `Shift` | Arm node and edge creation previews |
| `Esc` | Cancel a temporary creation preview |

## Running the application

You know, to be honest I'm not actually sure how to run this project from the
source code, but here are Chat's instructions. I'm trying to get a `.exe` file
put together so you can just download and run the program without fussing about
with python and stuff.

**Chat:** From the project directory, create or activate the project’s virtual
environment, then install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

Launch the application with:

```powershell
python main.py
```

Run the automated tests with:

```powershell
python -m pytest -q
```

## Planned work

The next things I want to include are some basic matrix features such as:

- Incidence matrices
- Distance matrices
- Full-size matrix viewing and export
- More matrix formatting options
- Save/load graphs
- Additional graph types and conventions for directed and weighted graphs
