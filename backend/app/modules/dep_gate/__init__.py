"""claim 门禁：互斥锁放行之后再过依赖闸门，仅前置 fulfilled 才允许认领。"""


def dep_claim_gate(depends_on, dep_status):
    """depends_on 为 None 直接放行；否则前置必须 fulfilled。

    dep_status 为 None 表示前置行缺失（悬挂依赖），同样拒绝。
    返回 {"ok": True} 或 {"ok": False, "code": ..., "depends_on": ...}，
    code 供前端钉出同一前置 id。
    """
    if depends_on is None:
        return {"ok": True}
    if dep_status is None:
        return {"ok": False, "code": "dep_missing", "depends_on": depends_on}
    if dep_status != "fulfilled":
        return {
            "ok": False,
            "code": "dep_blocked",
            "depends_on": depends_on,
            "dep_status": dep_status,
        }
    return {"ok": True}
