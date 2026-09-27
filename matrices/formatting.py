"""Formatting helpers for displaying and copying matrix results."""

from __future__ import annotations

import numpy as np


def format_scalar(value) -> str:
    """Format a scalar without unnecessary trailing ``.0`` text."""

    numeric_value = float(value)
    if np.isclose(numeric_value, round(numeric_value)):
        return str(int(round(numeric_value)))
    return f"{numeric_value:g}"


_format_number = format_scalar


def matrix_to_text(matrix: np.ndarray) -> str:
    """Return a readable, space-separated representation of a matrix."""

    array = np.asarray(matrix)
    if array.ndim != 2:
        raise ValueError("A matrix must be two-dimensional.")
    if array.size == 0:
        return ""

    return "\n".join(
        " ".join(format_scalar(value) for value in row)
        for row in array
    )


def matrix_to_mathematica(matrix: np.ndarray) -> str:
    """Return a matrix as a Mathematica-compatible nested list."""

    array = np.asarray(matrix)
    if array.ndim != 2:
        raise ValueError("A matrix must be two-dimensional.")
    if array.shape[0] == 0:
        return "{}"

    rows = [
        "{" + ",".join(format_scalar(value) for value in row) + "}"
        for row in array
    ]
    return "{" + ",".join(rows) + "}"
