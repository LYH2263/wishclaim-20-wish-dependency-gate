from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app import seed
from app.db import connect
from app.engines.claim_lock import claim_allowed, lock_payload, release_if_expired
from app.engines.dep_graph import validate_edge
from app.engines.dep_gate import dep_gate
from app.modules.dependency import attach, project

app = FastAPI(title="Wishclaim", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def _startup(): seed.init_db()

def now(): return datetime.now(timezone.utc)

def ttl():
    c = connect(); row = c.execute("SELECT value FROM settings WHERE key='ttl_seconds'").fetchone(); c.close()
    return int(row["value"] if row else 86400)

def sweep(c):
    for r in c.execute("SELECT * FROM wishes WHERE status='claimed'"):
        rel = release_if_expired(r["status"], r["expires_at"], now())
        if rel:
            c.execute("UPDATE wishes SET status=?, claimer=?, claimed_at=?, expires_at=? WHERE id=?",
                      (rel["status"], None, None, None, r["id"]))

def edges_map(c):
    return {r["id"]: r["depends_on"] for r in c.execute("SELECT id, depends_on FROM wishes")}

def all_by_id(c):
    return {r["id"]: dict(r) for r in c.execute("SELECT * FROM wishes")}

def check_edge(c, wid, depends_on):
    """Reject the save (400) when the dependency edge is invalid."""
    v = validate_edge(wid, depends_on, edges_map(c))
    if not v["ok"]:
        raise HTTPException(400, {"reason": v["reason"], "depends_on": v["depends_on"]})

@app.get("/api/health")
def health(): return {"ok": True, "project": "wishclaim"}

@app.get("/api/wishes")
def list_wishes():
    c = connect(); sweep(c); c.commit()
    rows = [dict(r) for r in c.execute("SELECT * FROM wishes ORDER BY id DESC")]; c.close()
    return attach(rows)

@app.get("/api/wishes/{wid}")
def get_wish(wid: int):
    c = connect(); sweep(c); c.commit()
    r = c.execute("SELECT * FROM wishes WHERE id=?", (wid,)).fetchone()
    if not r: c.close(); raise HTTPException(404, "not found")
    w = dict(r)
    pre = c.execute("SELECT * FROM wishes WHERE id=?", (w["depends_on"],)).fetchone() if w["depends_on"] else None
    c.close()
    w.update(project(w, dict(pre) if pre else None))
    return w

class WishIn(BaseModel):
    title: str
    note: str = ""
    depends_on: int | None = None

@app.post("/api/wishes")
def create_wish(body: WishIn):
    c = connect()
    check_edge(c, None, body.depends_on)
    cur = c.execute("INSERT INTO wishes(title,note,status,data_quality,depends_on) VALUES (?,?,?,?,?)",
                    (body.title, body.note, "open", "clean", body.depends_on))
    c.commit(); wid = cur.lastrowid; c.close(); return {"id": wid}

class DepIn(BaseModel):
    depends_on: int | None = None

@app.patch("/api/wishes/{wid}")
def set_dependency(wid: int, body: DepIn):
    c = connect()
    r = c.execute("SELECT id FROM wishes WHERE id=?", (wid,)).fetchone()
    if not r: c.close(); raise HTTPException(404, "not found")
    check_edge(c, wid, body.depends_on)
    c.execute("UPDATE wishes SET depends_on=? WHERE id=?", (body.depends_on, wid))
    c.commit(); c.close()
    return {"ok": True, "id": wid, "depends_on": body.depends_on}

class ClaimIn(BaseModel):
    claimer: str

@app.post("/api/wishes/{wid}/claim")
def claim(wid: int, body: ClaimIn):
    c = connect(); sweep(c); c.commit()
    r = c.execute("SELECT * FROM wishes WHERE id=?", (wid,)).fetchone()
    if not r: c.close(); raise HTTPException(404, "not found")
    allowed = claim_allowed(r["status"], r["claimer"], now(), r["expires_at"])
    if not allowed["ok"]:
        c.close(); raise HTTPException(409, allowed["reason"])
    pre_status = None
    if r["depends_on"] is not None:
        pre = c.execute("SELECT status FROM wishes WHERE id=?", (r["depends_on"],)).fetchone()
        pre_status = pre["status"] if pre else None
    gate = dep_gate(r["depends_on"], pre_status)
    if not gate["ok"]:
        c.close(); raise HTTPException(409, {"reason": gate["reason"], "depends_on": gate["depends_on"]})
    p = lock_payload(body.claimer, now(), ttl())
    c.execute("UPDATE wishes SET status=?, claimer=?, claimed_at=?, expires_at=? WHERE id=?",
              (p["status"], p["claimer"], p["claimed_at"], p["expires_at"], wid))
    c.commit(); c.close(); return p

@app.post("/api/wishes/{wid}/release")
def release(wid: int):
    c = connect()
    r = c.execute("SELECT * FROM wishes WHERE id=?", (wid,)).fetchone()
    if not r: c.close(); raise HTTPException(404, "not found")
    if r["status"] != "claimed":
        c.close(); raise HTTPException(400, "not_claimed")
    c.execute("UPDATE wishes SET status='released', claimer=NULL, claimed_at=NULL, expires_at=NULL WHERE id=?", (wid,))
    c.commit(); c.close(); return {"ok": True, "status": "released"}

@app.post("/api/wishes/{wid}/fulfill")
def fulfill(wid: int):
    c = connect()
    r = c.execute("SELECT * FROM wishes WHERE id=?", (wid,)).fetchone()
    if not r: c.close(); raise HTTPException(404, "not found")
    if r["status"] != "claimed":
        c.close(); raise HTTPException(400, "need_claim")
    c.execute("UPDATE wishes SET status='fulfilled' WHERE id=?", (wid,))
    c.commit(); c.close(); return {"ok": True, "status": "fulfilled"}

@app.post("/api/wishes/{wid}/unfulfill")
def unfulfill(wid: int):
    """Revoke a fulfillment back to open. Dependents already claimed keep
    their locks and surface dep_broken via the projection (see rules)."""
    c = connect()
    r = c.execute("SELECT * FROM wishes WHERE id=?", (wid,)).fetchone()
    if not r: c.close(); raise HTTPException(404, "not found")
    if r["status"] != "fulfilled":
        c.close(); raise HTTPException(400, "not_fulfilled")
    c.execute("UPDATE wishes SET status='open', claimer=NULL, claimed_at=NULL, expires_at=NULL WHERE id=?", (wid,))
    c.commit(); c.close(); return {"ok": True, "status": "open"}

@app.get("/api/mine")
def mine(claimer: str):
    c = connect(); sweep(c); c.commit()
    by_id = all_by_id(c)
    rows = [dict(r) for r in c.execute("SELECT * FROM wishes WHERE claimer=?", (claimer,))]; c.close()
    return attach(rows, by_id)

@app.get("/api/done")
def done():
    c = connect()
    rows = [dict(r) for r in c.execute("SELECT * FROM wishes WHERE status='fulfilled'")]; c.close(); return rows

@app.get("/api/settings")
def settings():
    c = connect(); rows = {r["key"]: r["value"] for r in c.execute("SELECT * FROM settings")}; c.close(); return rows

@app.get("/api/rules")
def rules():
    c = connect(); sweep(c); c.commit()
    by_id = all_by_id(c); c.close()
    dep_edges = [
        {"wish_id": w["id"], **project(w, by_id.get(w["depends_on"]))}
        for w in by_id.values() if w["depends_on"] is not None
    ]
    dep_edges.sort(key=lambda e: e["wish_id"])
    return {
        "mutex": "同一愿望同时只能被一人认领",
        "ttl": "认领超时未核销则自动释放",
        "fulfill": "核销后状态变为 fulfilled",
        "dependency": "愿望可挂 depends_on 前置；仅当前置核销（fulfilled）后才允许认领，未核销时墙卡与详情钉出同一前置 id",
        "dep_broken_policy": "前置核销被撤销（回到 open）时，后置已持有的认领保持有效并标记「依赖破裂」，前置重新核销后标记自动清除",
        "dep_edges": dep_edges,
    }
