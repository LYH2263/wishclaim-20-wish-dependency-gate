import os
import pytest
from fastapi.testclient import TestClient

@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from app.main import app
    from app import seed
    seed.init_db()
    return TestClient(app)

def mk(c, title, depends_on=None):
    r = c.post("/api/wishes", json={"title": title, "depends_on": depends_on})
    assert r.status_code == 200
    return r.json()["id"]

def test_claim_gate_blocks_until_prereq_fulfilled(client):
    pre = mk(client, "前置")
    dep = mk(client, "后置", depends_on=pre)
    r = client.post(f"/api/wishes/{dep}/claim", json={"claimer": "a"})
    assert r.status_code == 409 and r.json()["detail"]["reason"] == "dep_blocked"
    assert r.json()["detail"]["depends_on"] == pre
    # wall + detail pin the same prerequisite id while blocked
    assert client.get(f"/api/wishes/{dep}").json()["dep_blocked"] is True
    wall = {w["id"]: w for w in client.get("/api/wishes").json()}
    assert wall[dep]["dep_blocked"] is True and wall[dep]["depends_on"] == pre
    # fulfill the prerequisite -> gate opens immediately, badges clear
    client.post(f"/api/wishes/{pre}/claim", json={"claimer": "b"})
    client.post(f"/api/wishes/{pre}/fulfill")
    assert client.get(f"/api/wishes/{dep}").json()["dep_blocked"] is False
    assert client.post(f"/api/wishes/{dep}/claim", json={"claimer": "a"}).status_code == 200

def test_revoked_fulfillment_marks_broken_and_self_heals(client):
    pre = mk(client, "前置")
    dep = mk(client, "后置", depends_on=pre)
    client.post(f"/api/wishes/{pre}/claim", json={"claimer": "b"})
    client.post(f"/api/wishes/{pre}/fulfill")
    client.post(f"/api/wishes/{dep}/claim", json={"claimer": "a"})
    # revoke prerequisite fulfillment -> dependent keeps lock, flagged broken
    client.post(f"/api/wishes/{pre}/unfulfill")
    w = client.get(f"/api/wishes/{dep}").json()
    assert w["status"] == "claimed" and w["dep_broken"] is True and w["depends_on"] == pre
    mine = client.get("/api/mine", params={"claimer": "a"}).json()
    assert mine[0]["dep_broken"] is True and mine[0]["depends_on"] == pre
    # re-fulfill -> flag clears on all surfaces
    client.post(f"/api/wishes/{pre}/claim", json={"claimer": "b"})
    client.post(f"/api/wishes/{pre}/fulfill")
    assert client.get(f"/api/wishes/{dep}").json()["dep_broken"] is False
    assert client.get("/api/mine", params={"claimer": "a"}).json()[0]["dep_broken"] is False

def test_edge_validation_rejects_save(client):
    a = mk(client, "A")
    b = mk(client, "B", depends_on=a)
    # self dependency
    r = client.patch(f"/api/wishes/{a}", json={"depends_on": a})
    assert r.status_code == 400 and r.json()["detail"]["reason"] == "self_dependency"
    # cycle: B already depends on A
    r = client.patch(f"/api/wishes/{a}", json={"depends_on": b})
    assert r.status_code == 400 and r.json()["detail"]["reason"] == "dependency_cycle"
    # missing prerequisite on create
    r = client.post("/api/wishes", json={"title": "X", "depends_on": 999})
    assert r.status_code == 400 and r.json()["detail"]["reason"] == "dep_not_found"
    # graph unchanged after rejections
    assert client.get(f"/api/wishes/{a}").json()["depends_on"] is None

def test_rules_pin_dependency_edges(client):
    pre = mk(client, "前置")
    dep = mk(client, "后置", depends_on=pre)
    rules = client.get("/api/rules").json()
    assert "dependency" in rules and "dep_broken_policy" in rules
    edge = [e for e in rules["dep_edges"] if e["wish_id"] == dep][0]
    assert edge["depends_on"] == pre and edge["dep_blocked"] is True
