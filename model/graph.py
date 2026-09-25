"""Core graph data model.

The model deliberately knows nothing about Qt or how the graph is drawn.  That
separation lets the matrix code and file format use the same graph data as the
GUI.
"""

from __future__ import annotations

from typing import Iterable

from .edge import Edge
from .node import Node


class Graph:
    """A simple graph with positioned nodes and optional edge weights."""

    def __init__(self) -> None:
        self._nodes: dict[int, Node] = {}
        self._edges: list[Edge] = []
        self._next_id = 0

    @property
    def nodes(self) -> tuple[Node, ...]:
        return tuple(self._nodes.values())

    @property
    def edges(self) -> tuple[Edge, ...]:
        return tuple(self._edges)

    def to_dict(self) -> dict:
        """Return a complete serializable snapshot of the graph."""

        return {
            "nodes": [
                {
                    "id": node.id,
                    "label": node.label,
                    "x": node.x,
                    "y": node.y,
                }
                for node in self.nodes
            ],
            "edges": [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "weight": edge.weight,
                    "directed": edge.directed,
                }
                for edge in self.edges
            ],
        }

    def restore_from_dict(self, data: dict) -> None:
        """Replace this graph's contents with a serialized snapshot."""

        restored = Graph()
        for node in data.get("nodes", []):
            restored.add_node(
                node["x"],
                node["y"],
                node_id=node["id"],
                label=node.get("label"),
            )
        for edge in data.get("edges", []):
            restored.add_edge(
                edge["source"],
                edge["target"],
                weight=edge.get("weight", 1.0),
                directed=edge.get("directed", False),
            )

        self._nodes = restored._nodes
        self._edges = restored._edges
        self._next_id = restored._next_id

    def add_node(
        self,
        x: float,
        y: float,
        *,
        node_id: int | None = None,
        label: int | None = None,
    ) -> Node:
        """Add a node and return it.

        New labels follow creation order.  The distinction between internal IDs
        and visible labels will let us change renumbering behavior later without
        changing matrix or file-storage code.
        """

        if node_id is None:
            node_id = self._next_id
        if node_id in self._nodes:
            raise ValueError(f"A node with ID {node_id} already exists.")

        if label is None:
            label = len(self._nodes) + 1

        node = Node(id=node_id, x=float(x), y=float(y), label=label)
        self._nodes[node_id] = node
        self._next_id = max(self._next_id, node_id + 1)
        return node
        # This is kind of messy. I don't like how this is implemented.
        # I don't know why it's a good idea to allow us to give a new node
        # an ID of our choosing in the first place. It should be inaccessible,
        # so that it's just always assigned the next id in sequence.

    def get_node(self, node_id: int) -> Node:
        try:
            return self._nodes[node_id]
        except KeyError as error:
            raise KeyError(f"Unknown node ID: {node_id}") from error

    def remove_node(self, node_id: int) -> None:
        self.get_node(node_id)
        del self._nodes[node_id]
        self._edges = [
            edge
            for edge in self._edges
            if edge.source != node_id and edge.target != node_id
        ]
        self.relabel_nodes()

    def relabel_nodes(self) -> None:
        """Assign consecutive visible labels in the current node order."""

        for label, node in enumerate(self._nodes.values(), start=1):
            node.label = label

    def add_edge(
        self,
        source: int,
        target: int,
        *,
        weight: float = 1.0,
        directed: bool = False,
    ) -> Edge:
        """Add a simple edge between existing nodes."""

        if source == target:
            raise ValueError("Self-loops are not supported yet.")
        self.get_node(source)
        self.get_node(target)

        if self.has_edge(source, target, directed=directed):
            raise ValueError("That edge already exists.")

        edge = Edge(source, target, float(weight), directed)
        self._edges.append(edge)
        return edge

    def remove_edge(self, source: int, target: int) -> None:
        for index, edge in enumerate(self._edges):
            if self._same_connection(edge, source, target):
                del self._edges[index]
                return
        raise ValueError("That edge does not exist.")

    def has_edge(self, source: int, target: int, *, directed: bool = False) -> bool:
        return any(
            edge.directed == directed and self._same_connection(edge, source, target)
            for edge in self._edges
        )

    @staticmethod
    def _same_connection(edge: Edge, source: int, target: int) -> bool:
        if edge.directed:
            return edge.source == source and edge.target == target
        return {edge.source, edge.target} == {source, target}

    def node_ids(self) -> tuple[int, ...]:
        return tuple(self._nodes)

    def __len__(self) -> int:
        return len(self._nodes)

    def __iter__(self) -> Iterable[Node]:
        return iter(self.nodes)
