from app.engines.dep_gate import dep_gate

def test_no_dependency_is_open():
    assert dep_gate(None, None)["ok"] is True

def test_fulfilled_prerequisite_opens_gate():
    assert dep_gate(3, "fulfilled")["ok"] is True

def test_unfulfilled_prerequisite_blocks_and_pins_id():
    for st in ("open", "claimed", "released"):
        r = dep_gate(3, st)
        assert r["ok"] is False and r["reason"] == "dep_blocked" and r["depends_on"] == 3

def test_missing_prerequisite_blocks():
    r = dep_gate(3, None)
    assert r["ok"] is False and r["depends_on"] == 3
