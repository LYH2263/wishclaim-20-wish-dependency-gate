"""Dependency edge validation: existence, self-loop, cycle detection.

Pure functions over an adjacency mapping `edges: {wish_id: depends_on|None}`.
Used by both create and update paths; any failure rejects the save.
"""


def validate_edge(wid: int | None, depends_on: int | None, edges: dict) -> dict:
    """Validate setting `depends_on` on wish `wid` against the current graph.

    `wid` is None on create (the row does not exist yet, so self-loops and
    cycles through it are impossible; only existence is checked).
    Returns {"ok": True} or {"ok": False, "reason": <code>, "depends_on": id}.
    """
    if depends_on is None:
        return {"ok": True, "reason": ""}
    if wid is not None and depends_on == wid:
        return {"ok": False, "reason": "self_dependency", "depends_on": depends_on}
    if depends_on not in edges:
        return {"ok": False, "reason": "dep_not_found", "depends_on": depends_on}
    # Walk the chain from the new prerequisite; reaching `wid` means the new
    # edge would close a cycle. `seen` guards against pre-existing loops.
    seen = set()
    cur = depends_on
    while cur is not None and cur not in seen:
        if cur == wid:
            return {"ok": False, "reason": "dependency_cycle", "depends_on": depends_on}
        seen.add(cur)
        cur = edges.get(cur)
    return {"ok": True, "reason": ""}
