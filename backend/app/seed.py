from datetime import datetime, timedelta, timezone

from app.db import connect


def init_db():
    c = connect()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS wishes(
      id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, note TEXT, status TEXT,
      claimer TEXT, claimed_at TEXT, expires_at TEXT, data_quality TEXT,
      depends_on INTEGER
    );
    CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
    """)
    cols = {r["name"] for r in c.execute("PRAGMA table_info(wishes)")}
    if "depends_on" not in cols:
        c.execute("ALTER TABLE wishes ADD COLUMN depends_on INTEGER")
    if c.execute("SELECT COUNT(*) c FROM wishes").fetchone()["c"] == 0:
        now = datetime.now(timezone.utc)
        c.executemany(
            "INSERT INTO wishes(title,note,status,claimer,claimed_at,expires_at,data_quality,depends_on) VALUES (?,?,?,?,?,?,?,?)",
            [
                ("机械键盘", "红轴", "open", None, None, None, "clean", None),
                ("围巾", "羊毛", "open", None, None, None, "clean", None),
                ("脏愿望-空标题", "", "open", None, None, None, "dirty", None),
                ("过期锁样例", "应被TTL释放", "claimed", "ghost", "2020-01-01T00:00:00+00:00",
                 "2020-01-01T01:00:00+00:00", "dirty", None),
                ("键盘腕托", "等机械键盘核销（依赖灰态演示）", "open", None, None, None, "clean", 1),
                ("围巾收纳盒", "前置围巾未核销（依赖破裂演示）", "claimed", "seed",
                 now.isoformat(), (now + timedelta(days=1)).isoformat(), "clean", 2),
            ],
        )
        c.execute("INSERT INTO settings(key,value) VALUES ('ttl_seconds','86400')")
        c.execute("INSERT INTO settings(key,value) VALUES ('wall_title','暖粉愿望墙')")
    c.commit()
    c.close()
