"""Non-backtracking (Hashimoto) matrix generation."""

from __future__ import annotations

import numpy as np

from ..model import Graph


def nonbacktracking_matrix(graph: Graph) -> np.ndarray:
    """Return the non-backtracking matrix indexed by directed edge-arcs.

    Each undirected edge contributes two arcs.  A transition from ``u -> v``
    to ``x -> y`` is allowed when ``v == x`` and ``y != u``.  Directed-edge
    conventions will be refined when directed graphs are added to the GUI.
    """

    arcs: list[tuple[int, int]] = []
    for edge in graph.edges:
        arcs.append((edge.source, edge.target))
        if not edge.directed:
            arcs.append((edge.target, edge.source))

    matrix = np.zeros((len(arcs), len(arcs)), dtype=float)
    for row, (u, v) in enumerate(arcs):
        for column, (x, y) in enumerate(arcs):
            if v == x and y != u:
                matrix[row, column] = 1.0
    return matrix
