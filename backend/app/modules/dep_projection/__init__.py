"""投影：把 depends_on + 前置状态折算成墙 / 详情 / 我的认领共用的派生视图。

拍板口径：前置被撤销核销（回到 claimed/open）而后置已 claimed 时，
后置锁保持不自动释放，投影标记 dep_broken，三路同钉该口径；
前置重新 fulfilled（或后置被释放）后标记自动清除。
投影每次读取时实时推导，不落库，因此前置核销后角标立刻清除。
"""


def project(status, depends_on, dep_status):
    """单愿望投影。dep_status 为前置当前 status，缺失前置传 None。"""
    out = {"dep_status": dep_status, "dep_blocked": False, "dep_broken": False}
    if depends_on is None or dep_status == "fulfilled":
        return out
    if status in ("open", "released"):
        out["dep_blocked"] = True  # 灰态：前置未核销，不可领
    elif status == "claimed":
        out["dep_broken"] = True  # 破裂：锁保持，标记待恢复
    return out


def annotate(rows, by_id=None):
    """给每行补 dep_* 投影字段。by_id 缺省时用 rows 自身建 id 索引。"""
    if by_id is None:
        by_id = {r["id"]: r for r in rows}
    for r in rows:
        dep = r.get("depends_on")
        dep_row = by_id.get(dep) if dep is not None else None
        r.update(project(r["status"], dep, dep_row["status"] if dep_row else None))
    return rows
