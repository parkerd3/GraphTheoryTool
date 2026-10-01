import numpy as np

from GraphTheoryTool.matrices import (
    adjacency_matrix,
    degree_matrix,
    directed_arcs,
    ihara_matrix,
    laplacian_matrix,
    nonbacktracking_matrix,
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


def test_nonbacktracking_path_allows_continuation_but_not_reversal() -> None:
    graph = Graph()
    first = graph.add_node(0, 0)
    middle = graph.add_node(100, 0)
    last = graph.add_node(200, 0)
    graph.add_edge(first.id, middle.id)
    graph.add_edge(middle.id, last.id)
    snapshot = graph.to_dict()

    assert [(arc.index, arc.source, arc.target) for arc in directed_arcs(graph)] == [
        (1, first.id, middle.id), (2, middle.id, first.id),
        (3, middle.id, last.id), (4, last.id, middle.id),
    ]
    expected = np.zeros((4, 4))
    expected[0, 2] = 1  # first -> middle -> last
    expected[3, 1] = 1  # last -> middle -> first
    assert np.array_equal(nonbacktracking_matrix(graph), expected)
    assert graph.to_dict() == snapshot


def test_nonbacktracking_is_indexed_by_edges_even_with_isolated_nodes() -> None:
    graph = Graph()
    assert nonbacktracking_matrix(graph).shape == (0, 0)
    first = graph.add_node(0, 0)
    second = graph.add_node(100, 0)
    graph.add_node(200, 0)
    assert nonbacktracking_matrix(graph).shape == (0, 0)
    graph.add_edge(first.id, second.id)
    # An isolated vertex adds no arcs, and a single edge cannot be traversed
    # twice without immediately reversing direction.
    assert np.array_equal(nonbacktracking_matrix(graph), np.zeros((2, 2)))
