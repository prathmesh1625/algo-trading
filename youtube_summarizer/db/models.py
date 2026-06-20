CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS analyses (
    id          TEXT PRIMARY KEY,
    video_id    TEXT NOT NULL,
    url         TEXT NOT NULL,
    title       TEXT NOT NULL,
    channel     TEXT NOT NULL,
    duration    INTEGER DEFAULT 0,
    thumbnail   TEXT DEFAULT '',
    report_json TEXT NOT NULL,
    analyzed_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_video_id ON analyses(video_id);
CREATE INDEX IF NOT EXISTS idx_analyzed_at ON analyses(analyzed_at DESC);
"""
