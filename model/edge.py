"""Edge data for the graph model."""

from dataclasses import dataclass


@dataclass
class Edge:
    """An edge connecting two node IDs."""

    source: int
    target: int
    weight: float = 1.0
    directed: bool = False
