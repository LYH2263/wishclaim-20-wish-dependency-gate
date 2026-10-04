# Wishclaim · 礼物愿望认领

发布 → 认领锁定（互斥+TTL）→ 核销/释放。

| 服务 | 端口 |
| --- | --- |
| 前端 | 5200 |
| API | 10200 |

```bash
docker compose up --build
pytest backend/app/tests
```

依赖门禁：愿望可挂 `depends_on` 前置；仅当前置 `fulfilled` 后置才可认领，
墙卡灰态角标 / 详情不可领原因 / 规则页依赖边三路同钉同一前置 id。
禁止自依赖与环依赖，环检测失败拒保存（`POST /wishes`、`PUT /wishes/{id}/dep`）。

拍板口径：前置被撤销核销（`POST /wishes/{id}/revoke` → open）时后置已 `claimed`
→ 后置锁**保持**不自动释放，投影标记 `dep_broken`（依赖破裂），
墙 / 详情 / 我的认领同钉；破裂期间禁止核销后置，
待前置重新 `fulfilled` 或手动释放后置后恢复。

模块：`dep_validate`（依赖校验）/ `dep_gate`（claim 门禁）/ `dep_projection`（投影）。

0-1：`wish_comment` / `secret_santa` / `price_cap`。
