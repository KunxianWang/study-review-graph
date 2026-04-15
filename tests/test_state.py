from study_review_graph.state import StudyGraphState


def test_state_defaults_are_structured():
    state = StudyGraphState()
    assert state.course_name == "Untitled Course"
    assert state.raw_docs == []
    assert state.config.study_mode == "full_review"
    assert state.config.focus_topic is None
    assert state.review_notes.mode == "full_review"
    assert state.review_notes.concise_summary == []
    assert state.quality_report.next_actions == []


def test_state_round_trip_validation_smoke():
    state = StudyGraphState(
        course_name="Signals",
        user_goal="Understand transforms",
        config={"study_mode": "deep_dive", "focus_topic": "FFT"},
    )
    restored = StudyGraphState.model_validate(state.model_dump(mode="python"))
    assert restored.course_name == "Signals"
    assert restored.user_goal == "Understand transforms"
    assert restored.config.study_mode == "deep_dive"
    assert restored.config.focus_topic == "FFT"
