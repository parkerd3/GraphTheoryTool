"""Snapshot-based undo and redo support for graph editing."""

from __future__ import annotations

from .graph import Graph


class HistoryManager:
    """Maintain undo and redo stacks for graph model edits.

    A pending edit lets several low-level changes, such as an eraser drag,
    become one user-facing history entry.
    """

    def __init__(self, max_entries: int = 100) -> None:
        self.max_entries = max_entries
        self._undo_stack: list[dict] = []
        self._redo_stack: list[dict] = []
        self._pending_snapshot: dict | None = None

    @property
    def has_pending_edit(self) -> bool:
        return self._pending_snapshot is not None

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    def begin_edit(self, graph: Graph) -> None:
        """Capture the pre-edit state unless an edit is already in progress."""

        if self._pending_snapshot is None:
            self._pending_snapshot = graph.to_dict()

    def commit_edit(self, graph: Graph) -> None:
        """Commit a pending edit if it actually changed the graph."""

        if self._pending_snapshot is None:
            return

        current_snapshot = graph.to_dict()
        if current_snapshot != self._pending_snapshot:
            self._undo_stack.append(self._pending_snapshot)
            self._undo_stack = self._undo_stack[-self.max_entries :]
            self._redo_stack.clear()

        self._pending_snapshot = None

    def cancel_edit(self) -> None:
        """Discard a pending history entry without changing the graph."""

        self._pending_snapshot = None

    def undo(self, graph: Graph) -> bool:
        """Restore the most recent prior state."""

        self.commit_edit(graph)
        if not self._undo_stack:
            return False

        self._redo_stack.append(graph.to_dict())
        graph.restore_from_dict(self._undo_stack.pop())
        return True

    def redo(self, graph: Graph) -> bool:
        """Restore the most recently undone state."""

        self.commit_edit(graph)
        if not self._redo_stack:
            return False

        self._undo_stack.append(graph.to_dict())
        graph.restore_from_dict(self._redo_stack.pop())
        return True
