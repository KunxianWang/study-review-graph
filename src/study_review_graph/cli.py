"""CLI entrypoint for the study review workflow."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from study_review_graph.graph import invoke_study_graph
from study_review_graph.state import RuntimeConfig, StudyGraphState

app = typer.Typer(help="Build grounded study-review artifacts from course materials.")
console = Console()


@app.callback()
def main() -> None:
    """CLI group for study-review-graph commands."""


@app.command()
def run(
    input_dir: Path = typer.Option(Path("examples/input"), exists=True, file_okay=False),
    output_dir: Path = typer.Option(Path("examples/output/run")),
    course_name: str = typer.Option("Untitled Course"),
    user_goal: str = typer.Option("Deep understanding of the material."),
    chunk_size: int = typer.Option(900, min=200),
    chunk_overlap: int = typer.Option(120, min=0),
    top_k: int = typer.Option(5, min=1),
) -> None:
    """Run the study review graph on a local input directory."""

    initial_state = StudyGraphState(
        course_name=course_name,
        user_goal=user_goal,
        config=RuntimeConfig(
            input_dir=str(input_dir),
            output_dir=str(output_dir),
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            top_k=top_k,
        ),
    )

    final_state = invoke_study_graph(initial_state)

    console.print("study-review-graph outputs")
    for name, path in final_state.output_paths.items():
        console.print(f"- {name}: {path}")

    if final_state.warnings:
        console.print("[yellow]Warnings:[/yellow]")
        for warning in final_state.warnings:
            console.print(f"- {warning}")

    if final_state.errors:
        console.print("[red]Errors:[/red]")
        for error in final_state.errors:
            console.print(f"- {error}")


if __name__ == "__main__":
    app()
