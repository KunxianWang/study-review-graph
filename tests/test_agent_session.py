import shutil
from pathlib import Path
from uuid import uuid4

from study_review_graph.agents.session import SupervisorAgent, run_study_session
from study_review_graph.exporters.markdown import export_agent_session_markdown
from study_review_graph.state import (
    ConceptRecord,
    ExampleArtifact,
    FormulaArtifact,
    PracticeItem,
    ReviewNotes,
    SourceReference,
    StudyGraphState,
    WorkedSolution,
)


def test_supervisor_routes_formula_help_deterministically():
    routed = SupervisorAgent().route(request="请讲一下这个公式什么时候用")

    assert routed.intent == "formula_help"
    assert routed.selected_agent == "ConceptFormulaAgent"


def test_supervisor_routes_problem_walkthrough_to_example_agent():
    routed = SupervisorAgent().route(request="讲一下这道题")

    assert routed.intent == "example_help"
    assert routed.selected_agent == "ExampleSolutionAgent"


def test_supervisor_routes_how_to_solve_this_problem_to_example_agent():
    routed = SupervisorAgent().route(request="这题怎么做")

    assert routed.intent == "example_help"
    assert routed.selected_agent == "ExampleSolutionAgent"


def test_supervisor_routes_formula_example_request_to_example_agent():
    routed = SupervisorAgent().route(request="用这个公式给我讲一道例题")

    assert routed.intent == "example_help"
    assert routed.selected_agent == "ExampleSolutionAgent"


def test_supervisor_routes_practice_request_deterministically():
    routed = SupervisorAgent().route(request="给我来一道练习题")

    assert routed.intent == "practice_request"
    assert routed.selected_agent == "PracticeAgent"


def test_supervisor_routes_answer_check_when_practice_and_answer_present():
    routed = SupervisorAgent().route(
        request="帮我看看这道题答得对不对",
        practice_id="practice-formula-0",
        user_answer="我觉得应该用 F = m * a。",
    )

    assert routed.intent == "answer_check"
    assert routed.selected_agent == "AnswerCriticAgent"


def test_study_session_routes_to_practice_agent():
    state = _build_state()

    session_result, routed = run_study_session(
        state=state,
        request="给我一道公式应用练习",
    )

    assert routed.selected_agent == "PracticeAgent"
    assert session_result.detected_intent == "practice_request"
    assert session_result.selected_practice_id == "practice-formula-0"
    assert any("practice-formula-0" in line for line in session_result.response_lines)


def test_study_session_routes_to_answer_critic():
    state = _build_state()

    session_result, routed = run_study_session(
        state=state,
        request="请批改我的答案",
        practice_id="practice-formula-0",
        user_answer="先看净力、质量和加速度之间的关系，再确认质量可以视为常量，所以应该用 F = m * a。",
    )

    assert routed.selected_agent == "AnswerCriticAgent"
    assert session_result.answer_feedback is not None
    assert session_result.detected_intent == "answer_check"
    assert session_result.selected_practice_id == "practice-formula-0"


def test_study_session_returns_graceful_feedback_when_answer_missing():
    state = _build_state()

    session_result, routed = run_study_session(
        state=state,
        request="帮我批改 practice-formula-0",
    )

    assert routed.selected_agent == "AnswerCriticAgent"
    assert session_result.detected_intent == "answer_check"
    assert session_result.selected_practice_id == "practice-formula-0"
    assert any("缺少你的作答内容" in line for line in session_result.response_lines)


def test_study_session_returns_graceful_feedback_when_practice_id_missing():
    state = _build_state()

    session_result, routed = run_study_session(
        state=state,
        request="check my answer",
        user_answer="我觉得应该用 F = m * a。",
    )

    assert routed.selected_agent == "AnswerCriticAgent"
    assert session_result.detected_intent == "answer_check"
    assert session_result.selected_practice_id is None
    assert any("请补充 `practice_id`" in line for line in session_result.response_lines)


def test_agent_session_markdown_export_is_structured():
    state = _build_state()
    session_result, _routed = run_study_session(
        state=state,
        request="解释一下牛顿第二定律",
        focus_topic="Newton's Second Law",
    )
    temp_root = Path.cwd() / ".runtime_test_dirs"
    temp_root.mkdir(exist_ok=True)
    temp_dir = temp_root / f"agent-session-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        output_path = export_agent_session_markdown(session_result, output_dir=temp_dir)
        content = Path(output_path).read_text(encoding="utf-8")

        assert "# Agent Session" in content
        assert "检测到的意图" in content
        assert "选中的 Agent" in content
        assert "## Grounded References" in content
        assert "## Recommended Next Action" in content
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _build_state() -> StudyGraphState:
    reference = SourceReference(document_id="d1", source_path="notes.md", chunk_id="d1-chunk-0")
    return StudyGraphState(
        concepts=[
            ConceptRecord(
                concept_id="concept-0",
                name="Newton's Second Law",
                description="Relates force, mass, and acceleration.",
                references=[reference],
            )
        ],
        formulas=[
            FormulaArtifact(
                formula_id="formula-0",
                expression="F = m * a",
                symbol_explanations={"F": "net force", "m": "mass", "a": "acceleration"},
                conditions=["Use this law when the mass is treated as constant."],
                concept_links=["concept-0"],
                references=[reference],
            )
        ],
        examples=[
            ExampleArtifact(
                example_id="example-0",
                title="例题：牛顿第二定律",
                problem_statement="已知质量 2 kg、加速度 3 m/s^2，请利用 `F = m * a` 求净力。",
                formula_ids=["formula-0"],
                study_value="适合练习牛顿第二定律中的直接代入。",
                prompt="已知质量 2 kg、加速度 3 m/s^2，请利用 `F = m * a` 求净力。",
                formula_id="formula-0",
                references=[reference],
            )
        ],
        worked_solutions=[
            WorkedSolution(
                solution_id="solution-0",
                example_id="example-0",
                detailed_steps=[
                    "先写出 `F = m * a`。",
                    "再代入 `m = 2 kg` 和 `a = 3 m/s^2`。",
                    "最后得到 `F = 6 N`。",
                ],
                common_mistakes=["还没看清题目在求什么，就直接往公式里代数字。"],
                references=[reference],
            )
        ],
        review_notes=ReviewNotes(
            concise_summary=["本章主要围绕 Newton's Second Law 展开。"],
            common_mistakes=["还没看清题目在求什么，就直接往公式里代数字。"],
            study_questions=["看到 F = m * a 时先检查条件是否满足。"],
            references=[reference],
        ),
        practice_items=[
            PracticeItem(
                practice_id="practice-formula-0",
                question_type="formula_application",
                concept_ids=["concept-0"],
                formula_ids=["formula-0"],
                prompt="什么时候应该使用 `F = m * a`？",
                hint="先检查适用条件，再确认已知量和目标量。",
                expected_answer="应先说明净力、质量、加速度的关系，再说明适用条件。",
                references=[reference],
            )
        ],
    )
