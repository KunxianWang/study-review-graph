"""Export node wrapper."""

from __future__ import annotations

from study_review_graph.exporters.markdown import export_markdown_bundle
from study_review_graph.state import StudyGraphState


def export_outputs_node(state: StudyGraphState) -> dict[str, str]:
    """Write the markdown bundle to disk."""

    return export_markdown_bundle(state)
