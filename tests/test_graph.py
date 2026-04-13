from study_review_graph.graph import build_study_graph


def test_graph_construction_smoke():
    compiled = build_study_graph()
    assert compiled is not None
