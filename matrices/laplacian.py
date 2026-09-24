"""Degree and Laplacian matrix generation."""

import numpy as np

from ..model import Graph
from .adjacency import adjacency_matrix


def degree_matrix(graph: Graph) -> np.ndarray:
    """Return the diagonal degree matrix for the current graph."""

    adjacency = adjacency_matrix(graph)
    return np.diag(adjacency.sum(axis=1))


def laplacian_matrix(graph: Graph) -> np.ndarray:
    """Return the combinatorial Laplacian D - A."""

    return degree_matrix(graph) - adjacency_matrix(graph)
