"""Matrix-generation functions."""

from .adjacency import adjacency_matrix
from .formatting import format_scalar, matrix_to_mathematica, matrix_to_text
from .ihara import ihara_matrix
from .laplacian import degree_matrix, laplacian_matrix
from .nonbacktracking import nonbacktracking_matrix

__all__ = [
    "adjacency_matrix",
    "degree_matrix",
    "laplacian_matrix",
    "format_scalar",
    "ihara_matrix",
    "matrix_to_mathematica",
    "matrix_to_text",
    "nonbacktracking_matrix",
]
