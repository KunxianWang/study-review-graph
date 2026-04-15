"""Lightweight multi-agent orchestration over grounded study artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from study_review_graph.nodes.answer_check import check_answer_node, feedback_label_zh
from study_review_graph.state import AnswerFeedback, ConceptRecord, ExampleArtifact, FormulaArtifact, SourceReference, StudyGraphState, WorkedSolution

SessionIntent = Literal[
    "concept_help",
    "formula_help",
    "example_help",
    "practice_request",
    "answer_check",
    "review_guidance",
]


@dataclass
class RoutedRequest:
    """Supervisor decision for one study-session request."""

    intent: SessionIntent
    selected_agent: str
    rationale: str


@dataclass
class AgentSessionResult:
    """User-facing session output produced by the orchestration layer."""

    detected_intent: SessionIntent
    selected_agent: str
    response_title: str
    response_lines: list[str]
    references: list[SourceReference] = field(default_factory=list)
    recommended_next_action: str = ""
    selected_practice_id: str | None = None
    answer_feedback: AnswerFeedback | None = None
    warnings: list[str] = field(default_factory=list)


class SupervisorAgent:
    """Deterministic-first supervisor that routes to bounded specialist agents."""

    def route(
        self,
        *,
        request: str,
        practice_id: str | None = None,
        user_answer: str | None = None,
    ) -> RoutedRequest:
        normalized = request.lower()

        if practice_id and user_answer:
            return RoutedRequest(
                intent="answer_check",
                selected_agent="AnswerCriticAgent",
                rationale="检测到 practice_id 和作答文本，优先走答案批改路径。",
            )

        if any(keyword in normalized for keyword in ("check", "批改", "作答", "answer", "评分")):
            return RoutedRequest(
                intent="answer_check",
                selected_agent="AnswerCriticAgent",
                rationale="请求里包含答案检查类关键词。",
            )
        if any(keyword in normalized for keyword in ("practice", "练习", "quiz", "刷题", "题目")):
            return RoutedRequest(
                intent="practice_request",
                selected_agent="PracticeAgent",
                rationale="请求更像是在索取或浏览练习题。",
            )
        if any(keyword in normalized for keyword in ("example", "例题", "walkthrough", "solution", "推导", "演算")):
            return RoutedRequest(
                intent="example_help",
                selected_agent="ExampleSolutionAgent",
                rationale="请求聚焦于例题、步骤或解题讲解。",
            )
        if any(keyword in normalized for keyword in ("formula", "公式", "equation", "condition", "symbol", "符号", "假设")):
            return RoutedRequest(
                intent="formula_help",
                selected_agent="ConceptFormulaAgent",
                rationale="请求聚焦于公式、条件或符号解释。",
            )
        if any(keyword in normalized for keyword in ("review", "回看", "复习建议", "review next", "下一步")):
            return RoutedRequest(
                intent="review_guidance",
                selected_agent="ConceptFormulaAgent",
                rationale="请求聚焦于接下来该复习什么。",
            )
        return RoutedRequest(
            intent="concept_help",
            selected_agent="ConceptFormulaAgent",
            rationale="默认按概念理解类请求处理。",
        )


class ConceptFormulaAgent:
    """Handles concept explanation, formula clarification, and review guidance."""

    def handle(
        self,
        *,
        state: StudyGraphState,
        intent: SessionIntent,
        request: str,
        focus_topic: str | None,
    ) -> AgentSessionResult:
        concept = _match_concept(state, focus_topic or request)
        formula = _match_formula(state, focus_topic or request)

        if intent == "review_guidance":
            response_lines = (
                [*state.review_notes.concise_summary[:2]]
                + [f"当前最值得回看的易错点：{item}" for item in state.review_notes.common_mistakes[:2]]
                + [f"做题前先检查：{item}" for item in state.review_notes.study_questions[:2]]
            ) or ["TODO: 当前复习建议还需要更多 grounded artifact。"]
            references = _collect_reference_groups(
                [state.review_notes.references]
                + [concept.references if concept else []]
                + [formula.references if formula else []]
            )
            next_action = "建议先回看对应公式，再做一题 practice_set 里的练习。"
            title = "复习建议"
        else:
            response_lines = []
            if concept:
                response_lines.append(f"概念主线：{concept.name}")
                response_lines.append(concept.description or "TODO: 需要回原材料补概念描述。")
            if formula:
                response_lines.append(f"核心公式：`{formula.expression}`")
                if formula.symbol_explanations:
                    response_lines.extend(
                        f"- {symbol} 表示 {meaning}"
                        for symbol, meaning in list(formula.symbol_explanations.items())[:4]
                    )
                response_lines.append(
                    "条件提醒："
                    + (formula.conditions[0] if formula.conditions else "TODO: 需要确认适用条件。")
                )
            if not response_lines:
                response_lines.append("TODO: 当前请求没有稳定匹配到概念或公式，可尝试明确 focus_topic。")
            references = _collect_reference_groups(
                [concept.references if concept else []]
                + [formula.references if formula else []]
            )
            next_action = "建议下一步看对应 worked example，确认这个概念 / 公式如何真正落到题目里。"
            title = "概念 / 公式讲解"

        return AgentSessionResult(
            detected_intent=intent,
            selected_agent="ConceptFormulaAgent",
            response_title=title,
            response_lines=response_lines,
            references=references,
            recommended_next_action=next_action,
        )


class ExampleSolutionAgent:
    """Handles example retrieval and worked-solution walkthroughs."""

    def handle(
        self,
        *,
        state: StudyGraphState,
        request: str,
        focus_topic: str | None,
    ) -> AgentSessionResult:
        example = _match_example(state, focus_topic or request) or (state.examples[0] if state.examples else None)
        solution = _solution_for_example(state, example)

        if not example:
            return AgentSessionResult(
                detected_intent="example_help",
                selected_agent="ExampleSolutionAgent",
                response_title="例题讲解",
                response_lines=["TODO: 当前还没有可用例题，先运行主流程生成 worked examples。"],
                recommended_next_action="建议先运行 `run` 或 `study-session` 生成当前章节的例题与详解。",
            )

        response_lines = [
            f"例题：{example.title}",
            example.problem_statement or example.prompt or "TODO",
            f"这题在练什么：{example.study_value or 'TODO: 需要补充复习价值。'}",
        ]
        if solution and solution.detailed_steps:
            response_lines.append("关键步骤：")
            response_lines.extend(f"- {step}" for step in solution.detailed_steps[:4])
        if solution and solution.common_mistakes:
            response_lines.append(f"易错点：{solution.common_mistakes[0]}")

        references = _collect_reference_groups(
            [example.references]
            + [solution.references if solution else []]
        )
        next_action = "建议做一题同类 practice item，再用 check-answer 看自己是否真的掌握。"
        return AgentSessionResult(
            detected_intent="example_help",
            selected_agent="ExampleSolutionAgent",
            response_title="例题 / 解题讲解",
            response_lines=response_lines,
            references=references,
            recommended_next_action=next_action,
        )


class PracticeAgent:
    """Handles practice selection and presentation."""

    def handle(
        self,
        *,
        state: StudyGraphState,
        request: str,
    ) -> AgentSessionResult:
        requested_type = _practice_type_from_request(request)
        practice_items = state.practice_items
        if requested_type:
            practice_items = [item for item in practice_items if item.question_type == requested_type]

        if not practice_items:
            return AgentSessionResult(
                detected_intent="practice_request",
                selected_agent="PracticeAgent",
                response_title="练习题推荐",
                response_lines=["TODO: 当前没有匹配的练习题，可先运行主流程生成 practice_set。"],
                recommended_next_action="建议先生成 practice_set，或放宽请求条件后重试。",
            )

        lines = []
        for item in practice_items[:3]:
            lines.extend(
                [
                    f"`{item.practice_id}` - {_practice_type_label(item.question_type)}",
                    f"题目：{item.prompt}",
                    f"提示：{item.hint or 'TODO'}",
                    "",
                ]
            )
        references = _collect_reference_groups([item.references for item in practice_items[:3]])
        next_action = f"建议先做 `{practice_items[0].practice_id}`，然后用 `check-answer` 或 `study-session` 继续批改。"
        return AgentSessionResult(
            detected_intent="practice_request",
            selected_agent="PracticeAgent",
            response_title="练习题推荐",
            response_lines=_trim_blank(lines),
            references=references,
            recommended_next_action=next_action,
            selected_practice_id=practice_items[0].practice_id,
        )


class AnswerCriticAgent:
    """Handles answer checking and targeted review guidance."""

    def handle(
        self,
        *,
        state: StudyGraphState,
        practice_id: str | None,
        user_answer: str | None,
    ) -> AgentSessionResult:
        if not practice_id or not user_answer:
            raise ValueError("answer_check intent requires both practice_id and user answer.")

        feedback, warnings = check_answer_node(
            state,
            practice_id=practice_id,
            user_answer=user_answer,
        )
        lines = [
            f"结果判断：{feedback_label_zh(feedback.result_label)}",
            "关键问题：",
            *[f"- {item}" for item in feedback.key_issues],
            "正确思路：",
            *[f"- {item}" for item in feedback.correct_approach[:4]],
        ]
        next_action = feedback.review_guidance[0] if feedback.review_guidance else "建议先回看相关公式和例题。"
        return AgentSessionResult(
            detected_intent="answer_check",
            selected_agent="AnswerCriticAgent",
            response_title="作答反馈",
            response_lines=lines,
            references=feedback.references,
            recommended_next_action=next_action,
            selected_practice_id=feedback.practice_id,
            answer_feedback=feedback,
            warnings=warnings,
        )


def run_study_session(
    *,
    state: StudyGraphState,
    request: str,
    focus_topic: str | None = None,
    practice_id: str | None = None,
    user_answer: str | None = None,
) -> tuple[AgentSessionResult, RoutedRequest]:
    """Run one lightweight study session over the current grounded artifacts."""

    supervisor = SupervisorAgent()
    routed = supervisor.route(request=request, practice_id=practice_id, user_answer=user_answer)

    if routed.selected_agent == "AnswerCriticAgent":
        result = AnswerCriticAgent().handle(
            state=state,
            practice_id=practice_id,
            user_answer=user_answer,
        )
    elif routed.selected_agent == "PracticeAgent":
        result = PracticeAgent().handle(state=state, request=request)
    elif routed.selected_agent == "ExampleSolutionAgent":
        result = ExampleSolutionAgent().handle(
            state=state,
            request=request,
            focus_topic=focus_topic,
        )
    else:
        result = ConceptFormulaAgent().handle(
            state=state,
            intent=routed.intent,
            request=request,
            focus_topic=focus_topic,
        )
    return result, routed


def _match_concept(state: StudyGraphState, query: str | None) -> ConceptRecord | None:
    if not query:
        return state.concepts[0] if state.concepts else None
    normalized_query = _normalize_text(query)
    for concept in state.concepts:
        if normalized_query and normalized_query in _normalize_text(concept.name):
            return concept
    return state.concepts[0] if state.concepts else None


def _match_formula(state: StudyGraphState, query: str | None) -> FormulaArtifact | None:
    if not query:
        return state.formulas[0] if state.formulas else None
    normalized_query = _normalize_text(query)
    for formula in state.formulas:
        searchable = [formula.formula_id, formula.expression, *formula.symbol_explanations.values()]
        if any(normalized_query in _normalize_text(item) for item in searchable if item):
            return formula
    return state.formulas[0] if state.formulas else None


def _match_example(state: StudyGraphState, query: str | None) -> ExampleArtifact | None:
    if not query:
        return state.examples[0] if state.examples else None
    normalized_query = _normalize_text(query)
    for example in state.examples:
        if any(
            normalized_query in _normalize_text(item)
            for item in (example.title, example.problem_statement, example.example_id)
            if item
        ):
            return example
    return state.examples[0] if state.examples else None


def _solution_for_example(state: StudyGraphState, example: ExampleArtifact | None) -> WorkedSolution | None:
    if not example:
        return None
    for solution in state.worked_solutions:
        if solution.example_id == example.example_id:
            return solution
    return None


def _practice_type_from_request(request: str) -> str | None:
    normalized = request.lower()
    if any(keyword in normalized for keyword in ("概念", "concept")):
        return "concept_question"
    if any(keyword in normalized for keyword in ("公式", "formula")):
        return "formula_application"
    if any(keyword in normalized for keyword in ("计算", "calculation", "算")):
        return "worked_calculation"
    return None


def _collect_reference_groups(reference_groups: list[list[SourceReference]]) -> list[SourceReference]:
    references: list[SourceReference] = []
    seen: set[tuple[str, str | None]] = set()
    for group in reference_groups:
        for reference in group:
            key = (reference.source_path, reference.chunk_id)
            if key in seen:
                continue
            seen.add(key)
            references.append(reference)
    return references


def _normalize_text(text: str) -> str:
    return "".join(ch.lower() for ch in text if ch.isalnum())


def _trim_blank(lines: list[str]) -> list[str]:
    trimmed = list(lines)
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    return trimmed


def _practice_type_label(question_type: str) -> str:
    labels = {
        "concept_question": "概念题",
        "formula_application": "公式应用题",
        "worked_calculation": "典型计算题",
    }
    return labels.get(question_type, question_type)
