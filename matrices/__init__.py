"""Matrix-generation functions."""

from .adjacency import adjacency_matrix
from .laplacian import degree_matrix, laplacian_matrix
from .nonbacktracking import nonbacktracking_matrix

__all__ = [
    "adjacency_matrix",
    "degree_matrix",
    "laplacian_matrix",
    "nonbacktracking_matrix",
]
