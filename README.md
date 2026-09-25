# GraphTheoryTool

An educational graph editor and matrix generator for experimenting with graph theory.

## Current status

This repository contains the initial project structure and a minimal PySide6 window.
The main GUI elements and object creation and manipulation are being implemented.
Once user-interaction with the main canvas is mostly implemented, functions for
constructing the associated matrices will be the main focus.

## Running the application

From this directory:

```powershell
python -m pip install -r requirements.txt
python main.py
```

## Planned capabilities

- Interactive graph construction and editing
- Save/load using JSON
- Adjacency, Laplacian, incidence, and non-backtracking matrices
- Matrix preview, selection, copying, and export
