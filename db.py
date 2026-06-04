"""SQLite 数据库初始化与连接。"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from paths import get_data_dir

DATA_DIR = get_data_dir()
DB_PATH = DATA_DIR / "todo.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS item_types (
    type_key    TEXT PRIMARY KEY,
    type_name   TEXT NOT NULL,
    icon        TEXT DEFAULT '',
    color       TEXT DEFAULT '#1890ff',
    sort_order  INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS items (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    item_type            TEXT NOT NULL DEFAULT 'todo',
    title                TEXT NOT NULL,
    content              TEXT DEFAULT '',
    note                 TEXT DEFAULT '',
    scope                TEXT DEFAULT 'my',
    team_name            TEXT DEFAULT '',
    department_name      TEXT DEFAULT '',
    assignee_name        TEXT DEFAULT '',
    creator_name         TEXT DEFAULT '',
    status               TEXT DEFAULT 'open',
    priority             TEXT DEFAULT 'normal',
    is_recurring         INTEGER DEFAULT 0,
    frequency            TEXT DEFAULT NULL,
    recurrence_detail    TEXT DEFAULT NULL,
    recurrence_exceptions TEXT DEFAULT NULL,
    recurrence_next_date TEXT DEFAULT NULL,
    is_regular           INTEGER DEFAULT 0,
    parent_id            INTEGER DEFAULT NULL,
    start_date           TEXT DEFAULT NULL,
    start_time           TEXT DEFAULT NULL,
    due_date             TEXT DEFAULT NULL,
    due_time             TEXT DEFAULT NULL,
    checkpoint_date      TEXT DEFAULT NULL,
    completed_at         TEXT DEFAULT NULL,
    created_at           TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at           TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (item_type) REFERENCES item_types(type_key),
    FOREIGN KEY (parent_id) REFERENCES items(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS item_occurrences (
    item_id      INTEGER NOT NULL,
    exec_date    TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'open',
    completed_at TEXT DEFAULT NULL,
    PRIMARY KEY (item_id, exec_date),
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS activities (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id     INTEGER NOT NULL,
    author_name TEXT DEFAULT '',
    action      TEXT DEFAULT 'comment',
    content     TEXT DEFAULT '',
    created_at  TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_items_scope ON items(scope);
CREATE INDEX IF NOT EXISTS idx_items_status ON items(status);
CREATE INDEX IF NOT EXISTS idx_items_due ON items(due_date);
CREATE INDEX IF NOT EXISTS idx_items_parent ON items(parent_id);
"""

DEFAULT_TYPES = [
    ("todo", "个人待办", "📋", "#1890ff", 1),
    ("task", "任务", "✅", "#52c41a", 2),
    ("meeting", "会议", "📅", "#722ed1", 3),
    ("dept_todo", "部门待办", "🏢", "#13c2c2", 4),
    ("team_todo", "协作待办", "👥", "#fa8c16", 5),
]


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        for row in DEFAULT_TYPES:
            conn.execute(
                """
                INSERT OR IGNORE INTO item_types (type_key, type_name, icon, color, sort_order)
                VALUES (?, ?, ?, ?, ?)
                """,
                row,
            )


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


def rows_to_list(rows: list[sqlite3.Row]) -> list[dict]:
    return [row_to_dict(r) for r in rows]


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
