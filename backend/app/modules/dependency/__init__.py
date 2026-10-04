"""Dependency projection: derive the per-wish dependency view from wish rows.

Policy (拍板): when a prerequisite's fulfillment is revoked after the
dependent was claimed, the dependent's lock is KEPT and flagged
`dep_broken`; the flag is derived, so it clears automatically once the
prerequisite is fulfilled again. Wall / detail / mine all render this flag
pinning the same `depends_on` id.

Projection fields merged into each wish dict:
  depends_on   — prerequisite wish id (None = independent)
  dep_status   — prerequisite's current status ("missing" if not found)
  dep_blocked  — gate closed: prerequisite not fulfilled (claim is rejected)
  dep_broken   — lock held but prerequisite un-fulfilled after the fact
"""


def project(wish: dict, prereq: dict | None) -> dict:
    dep = wish.get("depends_on")
    if dep is None:
        return {"depends_on": None, "dep_status": None,
                "dep_blocked": False, "dep_broken": False}
    fulfilled = prereq is not None and prereq.get("status") == "fulfilled"
    return {
        "depends_on": dep,
        "dep_status": prereq.get("status") if prereq else "missing",
        "dep_blocked": not fulfilled,
        "dep_broken": wish.get("status") == "claimed" and not fulfilled,
    }


def attach(rows: list[dict], by_id: dict | None = None) -> list[dict]:
    """Merge the projection into every row in-place; returns rows."""
    if by_id is None:
        by_id = {r["id"]: r for r in rows}
    for r in rows:
        r.update(project(r, by_id.get(r.get("depends_on"))))
    return rows
