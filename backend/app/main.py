from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app import seed
from app.db import connect
from app.engines.claim_lock import claim_allowed, lock_payload, release_if_expired
from app.modules.dep_validate import validate_dep
from app.modules.dep_gate import dep_claim_gate
from app.modules.dep_projection import annotate, project

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

def fetch_wish(c, wid):
    return c.execute("SELECT * FROM wishes WHERE id=?", (wid,)).fetchone()

def dep_status_of(c, dep_id):
    if dep_id is None: return None
    r = c.execute("SELECT status FROM wishes WHERE id=?", (dep_id,)).fetchone()
    return r["status"] if r else None

def all_by_id(c):
    return {r["id"]: dict(r) for r in c.execute("SELECT * FROM wishes")}

@app.get("/api/health")
def health(): return {"ok": True, "project": "wishclaim"}

@app.get("/api/wishes")
def list_wishes():
    c = connect(); sweep(c); c.commit()
    rows = [dict(r) for r in c.execute("SELECT * FROM wishes ORDER BY id DESC")]; c.close()
    return annotate(rows)

@app.get("/api/wishes/{wid}")
def get_wish(wid: int):
    c = connect(); sweep(c); c.commit()
    r = fetch_wish(c, wid)
    if not r: c.close(); raise HTTPException(404, "not found")
    d = dict(r)
    d.update(project(d["status"], d["depends_on"], dep_status_of(c, d["depends_on"])))
    c.close(); return d

class WishIn(BaseModel):
    title: str
    note: str = ""
    depends_on: int | None = None

@app.post("/api/wishes")
def create_wish(body: WishIn):
    c = connect()
    v = validate_dep(None, body.depends_on, lambda i: fetch_wish(c, i))
    if not v["ok"]:
        c.close(); raise HTTPException(400, {"code": v["reason"], "depends_on": body.depends_on})
    cur = c.execute("INSERT INTO wishes(title,note,status,data_quality,depends_on) VALUES (?,?,?,?,?)",
                    (body.title, body.note, "open", "clean", body.depends_on))
    c.commit(); wid = cur.lastrowid; c.close(); return {"id": wid}

class DepIn(BaseModel):
    depends_on: int | None = None

@app.put("/api/wishes/{wid}/dep")
def set_dep(wid: int, body: DepIn):
    c = connect()
    r = fetch_wish(c, wid)
    if not r: c.close(); raise HTTPException(404, "not found")
    v = validate_dep(wid, body.depends_on, lambda i: fetch_wish(c, i))
    if not v["ok"]:
        c.close(); raise HTTPException(400, {"code": v["reason"], "depends_on": body.depends_on})
    c.execute("UPDATE wishes SET depends_on=? WHERE id=?", (body.depends_on, wid))
    c.commit(); c.close(); return {"ok": True, "id": wid, "depends_on": body.depends_on}

class ClaimIn(BaseModel):
    claimer: str

@app.post("/api/wishes/{wid}/claim")
def claim(wid: int, body: ClaimIn):
    c = connect(); sweep(c); c.commit()
    r = fetch_wish(c, wid)
    if not r: c.close(); raise HTTPException(404, "not found")
    allowed = claim_allowed(r["status"], r["claimer"], now(), r["expires_at"])
    if not allowed["ok"]:
        c.close(); raise HTTPException(409, allowed["reason"])
    gate = dep_claim_gate(r["depends_on"], dep_status_of(c, r["depends_on"]))
    if not gate["ok"]:
        c.close(); raise HTTPException(409, gate)
    p = lock_payload(body.claimer, now(), ttl())
    c.execute("UPDATE wishes SET status=?, claimer=?, claimed_at=?, expires_at=? WHERE id=?",
              (p["status"], p["claimer"], p["claimed_at"], p["expires_at"], wid))
    c.commit(); c.close(); return p

@app.post("/api/wishes/{wid}/release")
def release(wid: int):
    c = connect()
    r = fetch_wish(c, wid)
    if not r: c.close(); raise HTTPException(404, "not found")
    if r["status"] != "claimed":
        c.close(); raise HTTPException(400, "not_claimed")
    c.execute("UPDATE wishes SET status='released', claimer=NULL, claimed_at=NULL, expires_at=NULL WHERE id=?", (wid,))
    c.commit(); c.close(); return {"ok": True, "status": "released"}

@app.post("/api/wishes/{wid}/fulfill")
def fulfill(wid: int):
    c = connect()
    r = fetch_wish(c, wid)
    if not r: c.close(); raise HTTPException(404, "not found")
    if r["status"] != "claimed":
        c.close(); raise HTTPException(400, "need_claim")
    proj = project(r["status"], r["depends_on"], dep_status_of(c, r["depends_on"]))
    if proj["dep_broken"]:
        c.close(); raise HTTPException(409, {"code": "dep_broken", "depends_on": r["depends_on"]})
    c.execute("UPDATE wishes SET status='fulfilled' WHERE id=?", (wid,))
    c.commit(); c.close(); return {"ok": True, "status": "fulfilled"}

@app.post("/api/wishes/{wid}/revoke")
def revoke(wid: int):
    c = connect()
    r = fetch_wish(c, wid)
    if not r: c.close(); raise HTTPException(404, "not found")
    if r["status"] != "fulfilled":
        c.close(); raise HTTPException(400, "not_fulfilled")
    c.execute("UPDATE wishes SET status='open', claimer=NULL, claimed_at=NULL, expires_at=NULL WHERE id=?", (wid,))
    c.commit(); c.close(); return {"ok": True, "status": "open"}

@app.get("/api/mine")
def mine(claimer: str):
    c = connect(); sweep(c); c.commit()
    rows = [dict(r) for r in c.execute("SELECT * FROM wishes WHERE claimer=?", (claimer,))]
    by_id = all_by_id(c); c.close()
    return annotate(rows, by_id)

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
    by_id = all_by_id(c)
    rows = [dict(r) for r in c.execute("SELECT * FROM wishes WHERE depends_on IS NOT NULL ORDER BY id")]
    c.close()
    annotate(rows, by_id)
    edges = [
        {"wish": r["id"], "depends_on": r["depends_on"],
         "state": "broken" if r["dep_broken"] else "blocked" if r["dep_blocked"] else "ok"}
        for r in rows
    ]
    return {
        "mutex": "同一愿望同时只能被一人认领",
        "ttl": "认领超时未核销则自动释放",
        "fulfill": "核销后状态变为 fulfilled",
        "dep": "愿望可挂 depends_on 前置依赖：仅当前置 fulfilled，后置才允许认领；墙卡灰态角标 / 详情不可领原因 / 本页依赖边三路同钉同一前置 id",
        "dep_broken": "拍板口径：前置被撤销核销时后置已 claimed → 后置锁保持不自动释放，标记依赖破裂；破裂期间禁止核销后置，待前置重新 fulfilled 或手动释放后置后恢复",
        "dep_edges": edges,
    }
