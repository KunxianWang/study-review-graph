"""CLI entrypoint for the study review workflow."""

from __future__ import annotations

from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.console import Console

from study_review_graph.graph import invoke_study_graph
from study_review_graph.model_client import reset_model_client_cache, reset_model_response_cache
from study_review_graph.state import RuntimeConfig, StudyGraphState, StudyNoteMode

app = typer.Typer(help="Build grounded study-review artifacts from course materials.")
console = Console()


@app.callback()
def main() -> None:
    """CLI group for study-review-graph commands."""


@app.command()
def run(
    env_file: Path | None = typer.Option(
        None,
        exists=True,
        file_okay=True,
        dir_okay=False,
        help="Optional path to a local .env file with runtime model configuration.",
    ),
    input_dir: Path = typer.Option(Path("examples/input"), exists=True, file_okay=False),
    output_dir: Path = typer.Option(Path("examples/output/run")),
    course_name: str = typer.Option("Untitled Course"),
    user_goal: str = typer.Option("Deep understanding of the material."),
    chunk_size: int = typer.Option(900, min=200),
    chunk_overlap: int = typer.Option(120, min=0),
    top_k: int = typer.Option(5, min=1),
    study_mode: StudyNoteMode = typer.Option(
        "full_review",
        help="Study-note mode: full_review, deep_dive, or exam_sprint.",
    ),
    focus_topic: str | None = typer.Option(
        None,
        help="Optional concept, formula, or method to focus on in deep_dive mode.",
    ),
    include_practice_set: bool = typer.Option(
        True,
        "--include-practice-set/--skip-practice-set",
        help="Generate the grounded practice_set.md artifact.",
    ),
) -> None:
    """Run the study review graph on a local input directory."""

    _load_runtime_environment(env_file)

    initial_state = StudyGraphState(
        course_name=course_name,
        user_goal=user_goal,
        config=RuntimeConfig(
            input_dir=str(input_dir),
            output_dir=str(output_dir),
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            top_k=top_k,
            study_mode=study_mode,
            focus_topic=focus_topic,
            include_practice_set=include_practice_set,
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


def _load_runtime_environment(env_file: Path | None) -> None:
    """Load runtime env vars from an optional local .env file.

    An explicit env file should override stale shell variables so a deliberate
    runtime config wins over whatever happened to already be exported.
    """

    if env_file is not None:
        load_dotenv(dotenv_path=env_file, override=True)
    else:
        load_dotenv(override=False)

    reset_model_client_cache()
    reset_model_response_cache()
