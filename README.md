# Wishclaim · 礼物愿望认领

发布 → 认领锁定（互斥+TTL）→ 核销/释放。

依赖门禁：愿望可挂 `depends_on` 前置，仅当前置 fulfilled 才可认领；前置核销被撤销时，后置已持锁保持有效并标「依赖破裂」，重核销后自动恢复。依赖校验 `engines/dep_graph`、claim 门禁 `engines/dep_gate`、投影 `modules/dependency`。

| 服务 | 端口 |
| --- | --- |
| 前端 | 5200 |
| API | 10200 |

```bash
docker compose up --build
pytest backend/app/tests
```

0-1：`wish_comment` / `secret_santa` / `price_cap`。
