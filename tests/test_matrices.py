import numpy as np

from GraphTheoryTool.matrices import adjacency_matrix, laplacian_matrix
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
