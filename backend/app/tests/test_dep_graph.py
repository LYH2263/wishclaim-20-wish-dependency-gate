from app.engines.dep_graph import validate_edge

# graph: 1←2 (2 depends on 1), 3 independent
EDGES = {1: None, 2: 1, 3: None}

def test_self_dependency_rejected():
    r = validate_edge(1, 1, EDGES)
    assert r["ok"] is False and r["reason"] == "self_dependency" and r["depends_on"] == 1

def test_missing_prerequisite_rejected():
    r = validate_edge(3, 99, EDGES)
    assert r["ok"] is False and r["reason"] == "dep_not_found" and r["depends_on"] == 99

def test_direct_cycle_rejected():
    # 2 already depends on 1; pointing 1 back at 2 closes a loop
    r = validate_edge(1, 2, EDGES)
    assert r["ok"] is False and r["reason"] == "dependency_cycle"

def test_indirect_cycle_rejected():
    # chain 3→2→1, then 1→3 would close 1→3→2→1
    edges = {1: None, 2: 1, 3: 2}
    r = validate_edge(1, 3, edges)
    assert r["ok"] is False and r["reason"] == "dependency_cycle"

def test_valid_edge_accepted():
    assert validate_edge(3, 2, EDGES)["ok"] is True
    assert validate_edge(1, None, EDGES)["ok"] is True  # clearing is always fine

def test_create_path_only_checks_existence():
    # wid=None: the row does not exist yet, so self/cycle cannot form
    assert validate_edge(None, 2, EDGES)["ok"] is True
    assert validate_edge(None, 99, EDGES)["reason"] == "dep_not_found"
