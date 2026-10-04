from app.modules.dep_validate import validate_dep
from app.modules.dep_gate import dep_claim_gate
from app.modules.dep_projection import project, annotate


def table(rows):
    """rows: {id: depends_on} -> fetch 函数，模拟按 id 取愿望行。"""
    return lambda i: ({"id": i, "depends_on": rows[i]} if i in rows else None)


# ---- 依赖校验 ----

def test_self_dep_rejected():
    v = validate_dep(1, 1, table({1: None}))
    assert v["ok"] is False and v["reason"] == "self_dep"

def test_missing_dep_rejected():
    v = validate_dep(1, 99, table({1: None}))
    assert v["ok"] is False and v["reason"] == "dep_missing"

def test_cycle_rejected():
    # 已有 2 -> 3，挂 3 -> 2 闭合成环
    v = validate_dep(3, 2, table({2: 3, 3: None}))
    assert v["ok"] is False and v["reason"] == "dep_cycle"

def test_longer_cycle_rejected():
    # 已有 2 -> 3 -> 4，挂 4 -> 2 闭合成环
    v = validate_dep(4, 2, table({2: 3, 3: 4, 4: None}))
    assert v["ok"] is False and v["reason"] == "dep_cycle"

def test_chain_ok_and_clear_ok():
    fetch = table({2: None, 3: 2})
    assert validate_dep(4, 3, fetch)["ok"] is True  # 挂到已有链尾
    assert validate_dep(3, None, fetch)["ok"] is True  # 清除依赖恒合法

def test_create_skips_self_and_cycle():
    # 新建无 id：只校验前置存在，不可能自依赖/成环
    assert validate_dep(None, 2, table({2: None}))["ok"] is True
    v = validate_dep(None, 99, table({2: None}))
    assert v["ok"] is False and v["reason"] == "dep_missing"


# ---- claim 门禁 ----

def test_gate_blocks_until_fulfilled():
    for s in ("open", "claimed", "released"):
        g = dep_claim_gate(2, s)
        assert g["ok"] is False and g["code"] == "dep_blocked" and g["depends_on"] == 2
    assert dep_claim_gate(2, "fulfilled")["ok"] is True

def test_gate_no_dep_and_missing_dep():
    assert dep_claim_gate(None, None)["ok"] is True
    g = dep_claim_gate(2, None)
    assert g["ok"] is False and g["code"] == "dep_missing" and g["depends_on"] == 2


# ---- 投影 ----

def test_projection_blocked_and_clear():
    assert project("open", 2, "open")["dep_blocked"] is True
    assert project("released", 2, "claimed")["dep_blocked"] is True
    p = project("open", 2, "fulfilled")
    assert p["dep_blocked"] is False and p["dep_broken"] is False  # 前置核销即刻可领
    assert project("open", None, None) == {"dep_status": None, "dep_blocked": False, "dep_broken": False}

def test_projection_broken_policy_lock_kept():
    p = project("claimed", 2, "open")
    assert p["dep_broken"] is True and p["dep_blocked"] is False  # 锁保持 + 标破裂
    assert project("claimed", 2, "fulfilled")["dep_broken"] is False  # 前置重新核销后清除

def test_projection_missing_dep_blocks():
    assert project("open", 2, None)["dep_blocked"] is True
    assert project("claimed", 2, None)["dep_broken"] is True

def test_annotate_pins_same_dep_id():
    rows = [
        {"id": 1, "status": "open", "depends_on": None},
        {"id": 2, "status": "open", "depends_on": 1},
        {"id": 3, "status": "claimed", "depends_on": 1},
    ]
    annotate(rows)
    assert rows[1]["dep_blocked"] is True and rows[1]["depends_on"] == 1
    assert rows[2]["dep_broken"] is True and rows[2]["depends_on"] == 1
    assert rows[0]["dep_blocked"] is False and rows[0]["dep_broken"] is False
