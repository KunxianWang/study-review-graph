"""CLI entrypoint for the study review workflow."""

from __future__ import annotations

from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.console import Console

from study_review_graph.agents.session import run_study_session
from study_review_graph.exporters.markdown import export_agent_session_markdown, export_answer_feedback_markdown
from study_review_graph.graph import invoke_study_graph
from study_review_graph.model_client import reset_model_client_cache, reset_model_response_cache
from study_review_graph.nodes.answer_check import check_answer_node, feedback_label_zh
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

    initial_state = _build_initial_state(
        input_dir=input_dir,
        output_dir=output_dir,
        course_name=course_name,
        user_goal=user_goal,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        top_k=top_k,
        study_mode=study_mode,
        focus_topic=focus_topic,
        include_practice_set=include_practice_set,
    )

    final_state = invoke_study_graph(initial_state)

    console.print("study-review-graph outputs")
    for name, path in final_state.output_paths.items():
        console.print(f"- {name}: {path}")

    combined_warnings = list(final_state.warnings) + list(session_result.warnings)
    if combined_warnings:
        console.print("[yellow]Warnings:[/yellow]")
        for warning in combined_warnings:
            console.print(f"- {warning}")

    if final_state.errors:
        console.print("[red]Errors:[/red]")
        for error in final_state.errors:
            console.print(f"- {error}")


@app.command("study-session")
def study_session(
    env_file: Path | None = typer.Option(
        None,
        exists=True,
        file_okay=True,
        dir_okay=False,
        help="Optional path to a local .env file with runtime model configuration.",
    ),
    input_dir: Path = typer.Option(Path("examples/input"), exists=True, file_okay=False),
    output_dir: Path = typer.Option(Path("examples/output/study_session_run")),
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
    request: str = typer.Option(..., help="Study request, such as 概念讲解、例题讲解、生成练习、批改答案。"),
    practice_id: str | None = typer.Option(
        None,
        help="Optional practice id for answer-check or practice selection requests.",
    ),
    answer: str | None = typer.Option(None, help="Optional answer text for answer-check style requests."),
    answer_file: Path | None = typer.Option(
        None,
        exists=True,
        file_okay=True,
        dir_okay=False,
        help="Optional path to a text file containing the answer.",
    ),
) -> None:
    """Run a lightweight multi-agent study session over the grounded artifacts."""

    _load_runtime_environment(env_file)
    user_answer = _resolve_user_answer(answer=answer, answer_file=answer_file, required=False)
    initial_state = _build_initial_state(
        input_dir=input_dir,
        output_dir=output_dir,
        course_name=course_name,
        user_goal=user_goal,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        top_k=top_k,
        study_mode=study_mode,
        focus_topic=focus_topic,
        include_practice_set=True,
    )
    final_state = invoke_study_graph(initial_state)

    try:
        session_result, routed = run_study_session(
            state=final_state,
            request=request,
            focus_topic=focus_topic,
            practice_id=practice_id,
            user_answer=user_answer,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    session_path = export_agent_session_markdown(session_result, output_dir=output_dir)
    answer_feedback_path = None
    if session_result.answer_feedback is not None:
        answer_feedback_path = export_answer_feedback_markdown(
            session_result.answer_feedback,
            output_dir=output_dir,
        )

    console.print("study-review-graph agent session")
    console.print(f"- detected_intent: {routed.intent}")
    console.print(f"- selected_agent: {routed.selected_agent}")
    console.print(f"- agent_session: {session_path}")
    if answer_feedback_path:
        console.print(f"- answer_feedback: {answer_feedback_path}")
    console.print("response")
    for line in session_result.response_lines[:8]:
        console.print(f"- {line}")
    if session_result.recommended_next_action:
        console.print(f"- next_action: {session_result.recommended_next_action}")

    if final_state.warnings:
        console.print("[yellow]Warnings:[/yellow]")
        for warning in final_state.warnings:
            console.print(f"- {warning}")

    if final_state.errors:
        console.print("[red]Errors:[/red]")
        for error in final_state.errors:
            console.print(f"- {error}")


@app.command("check-answer")
def check_answer(
    env_file: Path | None = typer.Option(
        None,
        exists=True,
        file_okay=True,
        dir_okay=False,
        help="Optional path to a local .env file with runtime model configuration.",
    ),
    input_dir: Path = typer.Option(Path("examples/input"), exists=True, file_okay=False),
    output_dir: Path = typer.Option(Path("examples/output/check_answer_run")),
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
    practice_id: str = typer.Option(..., help="Practice item id to check, such as practice-formula-0."),
    answer: str | None = typer.Option(None, help="Direct answer text to evaluate."),
    answer_file: Path | None = typer.Option(
        None,
        exists=True,
        file_okay=True,
        dir_okay=False,
        help="Optional path to a text file containing the answer.",
    ),
) -> None:
    """Check one user answer against the current grounded practice set."""

    _load_runtime_environment(env_file)
    user_answer = _resolve_user_answer(answer=answer, answer_file=answer_file)

    initial_state = _build_initial_state(
        input_dir=input_dir,
        output_dir=output_dir,
        course_name=course_name,
        user_goal=user_goal,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        top_k=top_k,
        study_mode=study_mode,
        focus_topic=focus_topic,
        include_practice_set=True,
    )
    final_state = invoke_study_graph(initial_state)
    try:
        feedback, warnings = check_answer_node(
            final_state,
            practice_id=practice_id,
            user_answer=user_answer,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    feedback_path = export_answer_feedback_markdown(feedback, output_dir=output_dir)

    console.print("study-review-graph answer feedback")
    console.print(f"- practice_id: {feedback.practice_id}")
    console.print(f"- result: {feedback_label_zh(feedback.result_label)}")
    console.print(f"- answer_feedback: {feedback_path}")

    if feedback.key_issues:
        console.print("关键问题")
        for item in feedback.key_issues:
            console.print(f"- {item}")

    combined_warnings = list(final_state.warnings) + warnings
    if combined_warnings:
        console.print("[yellow]Warnings:[/yellow]")
        for warning in combined_warnings:
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


def _build_initial_state(
    *,
    input_dir: Path,
    output_dir: Path,
    course_name: str,
    user_goal: str,
    chunk_size: int,
    chunk_overlap: int,
    top_k: int,
    study_mode: StudyNoteMode,
    focus_topic: str | None,
    include_practice_set: bool,
) -> StudyGraphState:
    return StudyGraphState(
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


def _resolve_user_answer(*, answer: str | None, answer_file: Path | None, required: bool = True) -> str | None:
    if answer and answer.strip():
        return answer.strip()
    if answer_file is not None:
        text = answer_file.read_text(encoding="utf-8").strip()
        if text:
            return text
    if required:
        raise typer.BadParameter("Provide either --answer or --answer-file with non-empty content.")
    return None
