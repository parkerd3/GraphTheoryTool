import numpy as np

from GraphTheoryTool.matrices import (
    adjacency_matrix,
    degree_matrix,
    ihara_matrix,
    laplacian_matrix,
)
from GraphTheoryTool.model import Graph


def test_path_adjacency_and_laplacian() -> None:
    graph = Graph()
    first = graph.add_node(0, 0)
    middle = graph.add_node(1, 1)
    last = graph.add_node(2, 2)
    graph.add_edge(first.id, middle.id)
    graph.add_edge(middle.id, last.id)

    assert np.array_equal(
        adjacency_matrix(graph),
        np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]], dtype=float),
    )
    assert np.array_equal(
        laplacian_matrix(graph),
        np.array([[1, -1, 0], [-1, 2, -1], [0, -1, 1]], dtype=float),
    )
    assert np.array_equal(
        degree_matrix(graph),
        np.diag([1, 2, 1]).astype(float),
    )


def test_ihara_matrix_uses_the_requested_block_definition() -> None:
    graph = Graph()
    first = graph.add_node(0, 0)
    second = graph.add_node(1, 1)
    graph.add_edge(first.id, second.id)

    adjacency = np.array([[0, 1], [1, 0]], dtype=float)
    degree_minus_identity = np.zeros((2, 2), dtype=float)
    identity = np.eye(2, dtype=float)
    expected = np.block(
        [
            [adjacency, degree_minus_identity],
            [-identity, np.zeros((2, 2), dtype=float)],
        ]
    )

    assert np.array_equal(ihara_matrix(graph), expected)
