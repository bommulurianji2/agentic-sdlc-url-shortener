from agentic.policies import check_architecture_denylist, check_no_skipped_tests


def test_denylist_flags_banned_component():
    violations = check_architecture_denylist("We will deploy this on Kubernetes with Kafka.")
    assert "kubernetes" in violations
    assert "kafka" in violations


def test_denylist_passes_clean_architecture():
    assert check_architecture_denylist("A single FastAPI process with SQLite.") == []


def test_skipped_tests_are_flagged():
    violations = check_no_skipped_tests(["test_foo"])
    assert violations == ["test skipped without prior approval: test_foo"]


def test_no_skipped_tests_is_clean():
    assert check_no_skipped_tests([]) == []
