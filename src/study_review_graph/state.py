"""State and schema definitions for the study review workflow."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SourceReference(BaseModel):
    """Source traceability information for any generated artifact."""

    document_id: str
    source_path: str
    chunk_id: str | None = None
    page_number: int | None = None
    excerpt: str | None = None


class RawDocument(BaseModel):
    """Raw material loaded from disk."""

    document_id: str
    source_path: str
    media_type: str
    text: str
    metadata: dict[str, str] = Field(default_factory=dict)


class NormalizedDocument(BaseModel):
    """Normalized document content ready for chunking."""

    document_id: str
    source_path: str
    content: str
    sections: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)


class ChunkRecord(BaseModel):
    """Chunk used for deterministic retrieval and grounding."""

    chunk_id: str
    document_id: str
    source_path: str
    order: int
    text: str
    references: list[SourceReference] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)


class ConceptRecord(BaseModel):
    """Concept extracted from the source materials."""

    concept_id: str
    name: str
    description: str = ""
    related_formula_ids: list[str] = Field(default_factory=list)
    references: list[SourceReference] = Field(default_factory=list)


class FormulaArtifact(BaseModel):
    """Structured representation of a formula and supporting context."""

    formula_id: str
    expression: str
    symbol_explanations: dict[str, str] = Field(default_factory=dict)
    conditions: list[str] = Field(default_factory=list)
    concept_links: list[str] = Field(default_factory=list)
    references: list[SourceReference] = Field(default_factory=list)
    notes: str = ""


class ExampleArtifact(BaseModel):
    """Concrete example prompt tied to a formula or concept."""

    example_id: str
    title: str
    prompt: str
    formula_id: str | None = None
    reasoning_context: str = ""
    references: list[SourceReference] = Field(default_factory=list)


class WorkedSolution(BaseModel):
    """Stepwise solution explanation for an example."""

    solution_id: str
    example_id: str
    plan_steps: list[str] = Field(default_factory=list)
    detailed_steps: list[str] = Field(default_factory=list)
    rationale: list[str] = Field(default_factory=list)
    common_mistakes: list[str] = Field(default_factory=list)
    references: list[SourceReference] = Field(default_factory=list)


class ReviewNotes(BaseModel):
    """Primary study-note output bundle."""

    concise_summary: list[str] = Field(default_factory=list)
    detailed_explanations: list[str] = Field(default_factory=list)
    formula_highlights: list[str] = Field(default_factory=list)
    study_questions: list[str] = Field(default_factory=list)
    references: list[SourceReference] = Field(default_factory=list)


class QualityCheck(BaseModel):
    """A single evaluator result."""

    name: str
    status: str
    message: str


class QualityReport(BaseModel):
    """Collection of quality checks and follow-up actions."""

    groundedness_checks: list[QualityCheck] = Field(default_factory=list)
    formula_coverage_checks: list[QualityCheck] = Field(default_factory=list)
    explanation_completeness_checks: list[QualityCheck] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class RuntimeConfig(BaseModel):
    """Runtime configuration for the CLI and workflow."""

    input_dir: str = "examples/input"
    output_dir: str = "examples/output/run"
    chunk_size: int = 900
    chunk_overlap: int = 120
    top_k: int = 5
    enable_external_retrieval: bool = False
    enable_gemini_review: bool = False


class StudyGraphState(BaseModel):
    """Canonical workflow state shared across the graph."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    course_name: str = "Untitled Course"
    user_goal: str = "Deep understanding of the study material."
    raw_docs: list[RawDocument] = Field(default_factory=list)
    normalized_docs: list[NormalizedDocument] = Field(default_factory=list)
    chunks: list[ChunkRecord] = Field(default_factory=list)
    retrieval_cache: dict[str, list[str]] = Field(default_factory=dict)
    concepts: list[ConceptRecord] = Field(default_factory=list)
    formulas: list[FormulaArtifact] = Field(default_factory=list)
    examples: list[ExampleArtifact] = Field(default_factory=list)
    worked_solutions: list[WorkedSolution] = Field(default_factory=list)
    review_notes: ReviewNotes = Field(default_factory=ReviewNotes)
    output_paths: dict[str, str] = Field(default_factory=dict)
    quality_report: QualityReport = Field(default_factory=QualityReport)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    config: RuntimeConfig = Field(default_factory=RuntimeConfig)
