"""Ihara matrix generation."""

from __future__ import annotations

import numpy as np

try:
    from ..model import Graph
except ImportError:  # Supports importing matrices from a direct ``main.py`` run.
    from model import Graph

from .adjacency import adjacency_matrix
from .laplacian import degree_matrix


def ihara_matrix(graph: Graph) -> np.ndarray:
    """Return the 2n-by-2n Ihara block matrix.

    For an n-vertex graph, this implements the definition

        K = [[A, D - I],
             [-I, 0]],

    where A is the adjacency matrix and D is the degree matrix.
    """

    adjacency = adjacency_matrix(graph)
    degree = degree_matrix(graph)
    size = adjacency.shape[0]
    identity = np.eye(size, dtype=float)
    zero = np.zeros((size, size), dtype=float)

    return np.block(
        [
            [adjacency, degree - identity],
            [-identity, zero],
        ]
    )
