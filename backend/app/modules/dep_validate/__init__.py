"""依赖校验：保存 depends_on 边前的合法性检查（自依赖 / 前置缺失 / 环依赖）。"""


def validate_dep(wid, depends_on, fetch):
    """校验一条待保存的依赖边 wid -> depends_on。

    wid: 待保存愿望 id；新建时为 None（尚无 id，不可能自依赖或成环）。
    depends_on: 前置愿望 id，None 表示清除依赖（恒合法）。
    fetch: 按 id 取愿望行的函数，返回 None 表示不存在。
    返回 {"ok": True} 或 {"ok": False, "reason": "self_dep"|"dep_missing"|"dep_cycle"}。
    """
    if depends_on is None:
        return {"ok": True}
    if wid is not None and depends_on == wid:
        return {"ok": False, "reason": "self_dep"}
    if fetch(depends_on) is None:
        return {"ok": False, "reason": "dep_missing"}
    if wid is not None and _reaches(depends_on, wid, fetch):
        return {"ok": False, "reason": "dep_cycle"}
    return {"ok": True}


def _reaches(start, target, fetch):
    """从 start 沿 depends_on 链向上走，能到 target 则新边会闭合成环。"""
    seen = set()
    cur = start
    while cur is not None:
        if cur == target:
            return True
        if cur in seen:
            return False  # 链上历史遗留的环，不归本条新边负责
        seen.add(cur)
        row = fetch(cur)
        cur = row["depends_on"] if row else None
    return False
