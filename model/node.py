"""Vertex data for the graph model."""

from dataclasses import dataclass


@dataclass
class Node:
    """A graph vertex and its position on the drawing canvas."""

    id: int
    x: float
    y: float
    label: int
