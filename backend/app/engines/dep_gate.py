"""Dependency claim gate: a wish with depends_on is claimable only while its
prerequisite is fulfilled. Pure function; the route layer supplies the
prerequisite's current status. The blocked reason always pins the
prerequisite id so wall/detail/rules surfaces agree on it.
"""


def dep_gate(depends_on: int | None, prereq_status: str | None) -> dict:
    """Return {"ok": True} when the dependency gate is open.

    `prereq_status` is None when the prerequisite row is missing — treated as
    blocked (a fulfilled prerequisite can never be proven).
    """
    if depends_on is None:
        return {"ok": True, "reason": ""}
    if prereq_status == "fulfilled":
        return {"ok": True, "reason": ""}
    return {"ok": False, "reason": "dep_blocked", "depends_on": depends_on}
