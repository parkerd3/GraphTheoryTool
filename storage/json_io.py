"""JSON serialization for graph files."""

from __future__ import annotations

import json
from pathlib import Path

from ..model import Graph


def save_graph(graph: Graph, path: str | Path) -> None:
    """Save a graph to a human-readable JSON file."""

    data = {
        "nodes": [
            {"id": node.id, "label": node.label, "x": node.x, "y": node.y}
            for node in graph.nodes
        ],
        "edges": [
            {
                "source": edge.source,
                "target": edge.target,
                "weight": edge.weight,
                "directed": edge.directed,
            }
            for edge in graph.edges
        ],
    }
    Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_graph(path: str | Path) -> Graph:
    """Load a graph from a JSON file."""

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    graph = Graph()
    for node in data.get("nodes", []):
        graph.add_node(
            node["x"],
            node["y"],
            node_id=node["id"],
            label=node.get("label"),
        )
    for edge in data.get("edges", []):
        graph.add_edge(
            edge["source"],
            edge["target"],
            weight=edge.get("weight", 1.0),
            directed=edge.get("directed", False),
        )
    return graph
