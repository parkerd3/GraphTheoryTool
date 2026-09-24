"""Adjacency matrix generation."""

import numpy as np

from ..model import Graph


def adjacency_matrix(graph: Graph) -> np.ndarray:
    """Return the weighted adjacency matrix in graph-node order."""

    node_ids = graph.node_ids()
    index = {node_id: position for position, node_id in enumerate(node_ids)}
    matrix = np.zeros((len(node_ids), len(node_ids)), dtype=float)

    for edge in graph.edges:
        source = index[edge.source]
        target = index[edge.target]
        matrix[source, target] += edge.weight
        if not edge.directed:
            matrix[target, source] += edge.weight

    return matrix
