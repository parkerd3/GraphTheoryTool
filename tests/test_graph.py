from GraphTheoryTool.model import Graph


def test_graph_adds_nodes_and_edges() -> None:
    graph = Graph()
    first = graph.add_node(10, 20)
    second = graph.add_node(40, 50)
    graph.add_edge(first.id, second.id)

    assert [node.label for node in graph.nodes] == [1, 2]
    assert len(graph.edges) == 1


def test_removing_node_removes_incident_edges() -> None:
    graph = Graph()
    first = graph.add_node(0, 0)
    second = graph.add_node(1, 1)
    graph.add_edge(first.id, second.id)

    graph.remove_node(first.id)

    assert len(graph) == 1
    assert len(graph.edges) == 0


def test_removing_node_relabels_remaining_nodes() -> None:
    graph = Graph()
    first = graph.add_node(0, 0)
    second = graph.add_node(1, 1)
    third = graph.add_node(2, 2)

    graph.remove_node(second.id)

    assert [node.label for node in graph.nodes] == [1, 2]
    assert [node.id for node in graph.nodes] == [first.id, third.id]
