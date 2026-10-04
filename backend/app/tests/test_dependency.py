from app.modules.dependency import attach, project

PRE_FULFILLED = {"id": 1, "status": "fulfilled"}
PRE_OPEN = {"id": 1, "status": "open"}

def test_independent_wish_has_empty_projection():
    p = project({"id": 2, "status": "open", "depends_on": None}, None)
    assert p == {"depends_on": None, "dep_status": None, "dep_blocked": False, "dep_broken": False}

def test_blocked_until_prerequisite_fulfilled():
    w = {"id": 2, "status": "open", "depends_on": 1}
    p = project(w, PRE_OPEN)
    assert p["dep_blocked"] is True and p["dep_broken"] is False and p["dep_status"] == "open"
    p = project(w, PRE_FULFILLED)
    assert p["dep_blocked"] is False and p["dep_broken"] is False

def test_broken_when_lock_held_and_fulfillment_revoked():
    # 拍板: dependent keeps its claim, flagged dep_broken, self-heals on re-fulfill
    w = {"id": 2, "status": "claimed", "depends_on": 1}
    p = project(w, PRE_OPEN)
    assert p["dep_broken"] is True and p["depends_on"] == 1
    assert project(w, PRE_FULFILLED)["dep_broken"] is False

def test_fulfilled_dependent_is_not_broken():
    w = {"id": 2, "status": "fulfilled", "depends_on": 1}
    assert project(w, PRE_OPEN)["dep_broken"] is False

def test_missing_prerequisite_blocks():
    p = project({"id": 2, "status": "open", "depends_on": 9}, None)
    assert p["dep_status"] == "missing" and p["dep_blocked"] is True

def test_attach_projects_against_row_set():
    rows = [
        {"id": 1, "status": "fulfilled", "depends_on": None},
        {"id": 2, "status": "open", "depends_on": 1},
        {"id": 3, "status": "claimed", "depends_on": 2},
    ]
    attach(rows)
    assert rows[1]["dep_blocked"] is False               # prereq #1 fulfilled
    assert rows[2]["dep_blocked"] is True                # prereq #2 still open
    assert rows[2]["dep_broken"] is True                 # claimed while prereq unfulfilled
