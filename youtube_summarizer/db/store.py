import json
import sqlite3
import uuid
from datetime import datetime

from youtube_summarizer.config import DB_PATH
from youtube_summarizer.db.models import CREATE_TABLE_SQL


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def init_db() -> None:
    with _conn() as con:
        for stmt in CREATE_TABLE_SQL.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                con.execute(stmt)
        con.commit()


def save_analysis(
    video_id: str,
    url: str,
    title: str,
    channel: str,
    duration: int,
    thumbnail: str,
    report: dict,
) -> str:
    aid = uuid.uuid4().hex[:8]
    analyzed_at = datetime.now().isoformat()
    with _conn() as con:
        con.execute(
            "INSERT INTO analyses VALUES (?,?,?,?,?,?,?,?,?)",
            (aid, video_id, url, title, channel, duration, thumbnail,
             json.dumps(report, ensure_ascii=False), analyzed_at),
        )
        con.commit()
    return aid


def get_analysis(aid: str) -> dict | None:
    with _conn() as con:
        row = con.execute("SELECT * FROM analyses WHERE id = ?", (aid,)).fetchone()
    if not row:
        return None
    data = dict(row)
    data["report"] = json.loads(data.pop("report_json"))
    return data


def get_by_video_id(video_id: str) -> dict | None:
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM analyses WHERE video_id = ? ORDER BY analyzed_at DESC LIMIT 1",
            (video_id,),
        ).fetchone()
    if not row:
        return None
    data = dict(row)
    data["report"] = json.loads(data.pop("report_json"))
    return data


def get_history(limit: int = 50) -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT id, video_id, url, title, channel, duration, thumbnail, analyzed_at "
            "FROM analyses ORDER BY analyzed_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_analysis(aid: str) -> bool:
    with _conn() as con:
        cur = con.execute("DELETE FROM analyses WHERE id = ?", (aid,))
        con.commit()
    return cur.rowcount > 0
