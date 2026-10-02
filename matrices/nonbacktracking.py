"""Non-backtracking (Hashimoto) matrix generation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

try:
    from ..model import Graph
except ImportError:  # Supports importing matrices from a direct ``main.py`` run.
    from model import Graph


@dataclass(frozen=True)
class DirectedEdge:
    """A numbered orientation of a graph edge, derived without editing it."""

    index: int
    source: int
    target: int


def directed_arcs(graph: Graph) -> tuple[DirectedEdge, ...]:
    """List arcs in edge-creation order, with reverse arcs immediately after.

    Arc indices start at 1 and correspond to matrix row and column headers.
    Endpoints retain the graph's stable internal node IDs.
    """

    arcs = []
    for edge in graph.edges:
        arcs.append(DirectedEdge(len(arcs) + 1, edge.source, edge.target))
        if not edge.directed:
            arcs.append(DirectedEdge(len(arcs) + 1, edge.target, edge.source))
    return tuple(arcs)


def nonbacktracking_matrix(graph: Graph) -> np.ndarray:
    """Return the non-backtracking matrix indexed by directed edge-arcs.

    Each undirected edge contributes two arcs.  A transition from ``u -> v``
    to ``x -> y`` is allowed when ``v == x`` and ``y != u``.  Directed-edge
    conventions will be refined when directed graphs are added to the GUI.
    """

    arcs = directed_arcs(graph)

    matrix = np.zeros((len(arcs), len(arcs)), dtype=float)
    for row, incoming in enumerate(arcs):
        for column, outgoing in enumerate(arcs):
            if (
                incoming.target == outgoing.source
                and outgoing.target != incoming.source
            ):
                matrix[row, column] = 1.0
    return matrix
