from agentic import graph, state


def test_graph_has_no_structural_violations():
    assert graph.validate_graph() == []


def test_every_node_has_a_status_mapping_or_is_terminal():
    for node in graph.NODES:
        if graph.is_terminal(node):
            continue
        assert node in state.STAGE_TO_STATUS, f"{node} has no coarse-status mapping"


def test_security_review_has_the_corrected_fail_path():
    # ADR-007: the master brief's own diagram omitted this edge.
    outcomes = graph.NODES["SECURITY_REVIEW"]["next"]
    assert outcomes["critical"] == "SAFE_STOP"
    assert outcomes["non_critical"] == "RETRY_EVALUATION"
    assert outcomes["pass"] == "DOCUMENTATION"


def test_human_gate_architecture_fans_out_to_parallel_branch():
    assert set(graph.next_nodes("HUMAN_GATE_ARCHITECTURE")) == {"IMPLEMENTATION", "TEST_DESIGN"}


def test_join_waits_on_both_parallel_branches():
    assert set(graph.NODES["JOIN"]["join_of"]) == {"IMPLEMENTATION", "TEST_DESIGN"}


def test_retry_evaluation_routes_correctly():
    assert graph.next_node("RETRY_EVALUATION", "retry") == "IMPLEMENTATION"
    assert graph.next_node("RETRY_EVALUATION", "exhausted") == "ROLLBACK"


def test_only_completed_status_can_release():
    assert state.can_release("COMPLETED") is True
    for blocked in ("SAFE_STOPPED", "REJECTED", "FAILED", "TESTING"):
        assert state.can_release(blocked) is False
