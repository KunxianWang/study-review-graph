"""Compatibility helpers for minimal local environments.

The project prefers LangGraph and LangChain components when available.
For v0.1 scaffolding, lightweight fallbacks keep the repository runnable
even before optional dependencies are installed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

try:
    from langgraph.graph import END, START, StateGraph
except ModuleNotFoundError:
    START = "__start__"
    END = "__end__"

    @dataclass
    class _CompiledStateGraph:
        nodes: dict[str, Callable[[dict[str, Any]], dict[str, Any]]]
        edges: dict[str, list[str]]

        def invoke(self, state: dict[str, Any]) -> dict[str, Any]:
            current = self.edges[START][0]
            working = dict(state)
            while current != END:
                update = self.nodes[current](working) or {}
                working.update(update)
                current = self.edges.get(current, [END])[0]
            return working

    class StateGraph:
        """Minimal linear workflow fallback used only when LangGraph is unavailable."""

        def __init__(self, _state_type: Any):
            self._nodes: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {}
            self._edges: dict[str, list[str]] = {}

        def add_node(self, name: str, func: Callable[[dict[str, Any]], dict[str, Any]]) -> None:
            self._nodes[name] = func

        def add_edge(self, source: str, target: str) -> None:
            self._edges.setdefault(source, []).append(target)

        def compile(self) -> _CompiledStateGraph:
            return _CompiledStateGraph(nodes=self._nodes, edges=self._edges)

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ModuleNotFoundError:
    class RecursiveCharacterTextSplitter:
        """Simple text splitter fallback with overlap support."""

        def __init__(self, chunk_size: int, chunk_overlap: int):
            self.chunk_size = chunk_size
            self.chunk_overlap = chunk_overlap

        def split_text(self, text: str) -> list[str]:
            if not text:
                return []

            chunks: list[str] = []
            step = max(1, self.chunk_size - self.chunk_overlap)
            start = 0
            while start < len(text):
                chunk = text[start : start + self.chunk_size].strip()
                if chunk:
                    chunks.append(chunk)
                start += step
            return chunks
