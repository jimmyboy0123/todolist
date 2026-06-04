"""Todo List — 个人事项 & 日历视图（无需登录）。"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory
from werkzeug.utils import secure_filename

import calendar_service as cal
from db import get_conn, init_db, now_str, row_to_dict, rows_to_list
from paths import get_resource_dir, get_uploads_dir

_res = get_resource_dir()
app = Flask(
    __name__,
    template_folder=str(_res / "templates"),
    static_folder=str(_res / "static"),
)
init_db()

VALID_STATUS = {"draft", "open", "in_progress", "pending_review", "done", "archived"}
VALID_PRIORITY = {"urgent", "high", "normal", "low"}
VALID_SCOPE = {"my", "team", "department", "company"}
MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024
BLOCKED_EXTENSIONS = {".exe", ".bat", ".cmd", ".sh", ".ps1", ".msi", ".dll", ".scr"}


def ok(**payload):
    return jsonify({"ok": True, **payload})


def err(msg: str, code: int = 400):
    return jsonify({"ok": False, "msg": msg}), code


def enrich_item(item: dict) -> dict:
    item = dict(item)
    item["status_info"] = cal.STATUS_MAP.get(item.get("status"), {"name": item.get("status"), "color": "#999"})
    item["priority_info"] = cal.PRIORITY_MAP.get(
        item.get("priority"), {"name": item.get("priority"), "color": "#999", "icon": ""}
    )
    item["is_recurring"] = bool(item.get("is_recurring"))
    item["is_regular"] = bool(item.get("is_regular"))
    if item.get("parent_id"):
        item["parent_id"] = int(item["parent_id"])
    else:
        item["parent_id"] = None
    return item


def enrich_attachment_counts(items: list[dict]) -> list[dict]:
    ids = list({int(i["id"]) for i in items if i.get("id")})
    if not ids:
        return items
    placeholders = ",".join("?" * len(ids))
    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT item_id, COUNT(*) AS cnt FROM item_attachments
            WHERE item_id IN ({placeholders}) GROUP BY item_id
            """,
            ids,
        ).fetchall()
    counts = {int(r["item_id"]): int(r["cnt"]) for r in rows}
    for item in items:
        item["attachment_count"] = counts.get(int(item["id"]), 0)
    return items


def format_day_item(item: dict, date_str: str) -> dict:
    item = enrich_item(item)
    due = item.get("due_date") or ""
    if due == "2999-12-31":
        due = ""
    item["due_date"] = due
    if item.get("is_recurring") and item.get("occurrence_status"):
        item["status"] = item["occurrence_status"]
        if item.get("occurrence_completed_at"):
            item["completed_at"] = item["occurrence_completed_at"]
    elif item.get("is_recurring") and item.get("status") == "done":
        item["status"] = "open"
        item["completed_at"] = ""
    if not item.get("execution_date") and not item.get("is_recurring"):
        item["execution_date"] = date_str
    return item


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/hub")
def hub_page():
    return render_template("hub.html")


@app.route("/calendar")
def calendar_page():
    return render_template("calendar.html")


@app.route("/api/meta")
def api_meta():
    with get_conn() as conn:
        types = rows_to_list(conn.execute("SELECT * FROM item_types ORDER BY sort_order").fetchall())
    return ok(
        types=types,
        statuses=cal.STATUS_MAP,
        priorities=cal.PRIORITY_MAP,
        scopes=list(VALID_SCOPE),
    )


@app.route("/api/items", methods=["GET"])
def api_items_list():
    scope = request.args.get("scope", "my")
    status = request.args.get("status", "")
    q = request.args.get("q", "").strip()
    parent_only = request.args.get("parent_only", "1") == "1"
    team_name = request.args.get("team_name", "")
    dept_name = request.args.get("department_name", "")
    page = max(1, int(request.args.get("page", 1)))
    limit = 50
    offset = (page - 1) * limit

    where = ["i.status != 'archived'"]
    params: list = []

    if scope in VALID_SCOPE:
        where.append("i.scope = ?")
        params.append(scope)
    if status and status != "all":
        where.append("i.status = ?")
        params.append(status)
    if parent_only:
        where.append("i.parent_id IS NULL")
    if team_name and scope == "team":
        where.append("i.team_name = ?")
        params.append(team_name)
    if dept_name and scope == "department":
        where.append("i.department_name = ?")
        params.append(dept_name)
    if q:
        where.append("(i.title LIKE ? OR i.content LIKE ? OR i.note LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like, like])

    where_sql = " AND ".join(where)
    with get_conn() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM items i WHERE {where_sql}", params).fetchone()[0]
        rows = conn.execute(
            f"""
            SELECT i.*, t.type_name, t.icon AS type_icon, t.color AS type_color,
                   (SELECT COUNT(*) FROM items c WHERE c.parent_id = i.id) AS child_count
            FROM items i
            LEFT JOIN item_types t ON t.type_key = i.item_type
            WHERE {where_sql}
            ORDER BY i.created_at DESC
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        ).fetchall()

    items = [enrich_item(row_to_dict(r)) for r in rows]
    return ok(items=items, total=total, page=page, pages=max(1, (total + limit - 1) // limit))


@app.route("/api/items/<int:item_id>", methods=["GET"])
def api_item_detail(item_id: int):
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT i.*, t.type_name, t.icon AS type_icon, t.color AS type_color
            FROM items i
            LEFT JOIN item_types t ON t.type_key = i.item_type
            WHERE i.id = ?
            """,
            [item_id],
        ).fetchone()
        if not row:
            return err("事项不存在", 404)
        children = rows_to_list(
            conn.execute("SELECT * FROM items WHERE parent_id = ? ORDER BY created_at ASC", [item_id]).fetchall()
        )
        activities = rows_to_list(
            conn.execute(
                "SELECT * FROM activities WHERE item_id = ? ORDER BY created_at DESC", [item_id]
            ).fetchall()
        )
        att_rows = rows_to_list(
            conn.execute(
                "SELECT * FROM item_attachments WHERE item_id = ? ORDER BY created_at DESC", [item_id]
            ).fetchall()
        )
    return ok(
        item=enrich_item(row_to_dict(row)),
        children=[enrich_item(c) for c in children],
        activities=activities,
        attachments=[_format_attachment(r) for r in att_rows],
    )


@app.route("/api/items", methods=["POST"])
def api_item_create():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return err("标题不能为空")

    scope = data.get("scope", "my")
    if scope not in VALID_SCOPE:
        scope = "my"

    fields = {
        "item_type": data.get("item_type", "todo"),
        "title": title,
        "content": (data.get("content") or "").strip(),
        "note": (data.get("note") or "").strip(),
        "scope": scope,
        "team_name": (data.get("team_name") or "").strip(),
        "department_name": (data.get("department_name") or "").strip(),
        "assignee_name": (data.get("assignee_name") or "").strip(),
        "creator_name": (data.get("creator_name") or "").strip(),
        "status": data.get("status", "open"),
        "priority": data.get("priority", "normal"),
        "is_recurring": 1 if data.get("is_recurring") else 0,
        "frequency": data.get("frequency") or None,
        "recurrence_detail": json.dumps(data.get("recurrence_detail") or {}, ensure_ascii=False) if data.get("recurrence_detail") else None,
        "is_regular": 1 if data.get("is_regular") else 0,
        "parent_id": int(data["parent_id"]) if data.get("parent_id") else None,
        "start_date": data.get("start_date") or None,
        "start_time": data.get("start_time") or None,
        "due_date": data.get("due_date") or None,
        "due_time": data.get("due_time") or None,
        "checkpoint_date": data.get("checkpoint_date") or None,
    }

    if fields["status"] not in VALID_STATUS:
        fields["status"] = "open"
    if fields["priority"] not in VALID_PRIORITY:
        fields["priority"] = "normal"

    cols = ", ".join(fields.keys())
    placeholders = ", ".join("?" * len(fields))
    with get_conn() as conn:
        cur = conn.execute(f"INSERT INTO items ({cols}) VALUES ({placeholders})", list(fields.values()))
        new_id = cur.lastrowid
    return ok(id=new_id)


@app.route("/api/items/<int:item_id>", methods=["PUT"])
def api_item_update(item_id: int):
    data = request.get_json(silent=True) or {}
    allowed = {
        "item_type", "title", "content", "note", "scope", "team_name", "department_name",
        "assignee_name", "creator_name", "status", "priority", "is_recurring", "frequency",
        "recurrence_detail", "recurrence_exceptions", "recurrence_next_date", "is_regular",
        "parent_id", "start_date", "start_time", "due_date", "due_time", "checkpoint_date",
    }
    updates: dict = {}
    for k, v in data.items():
        if k not in allowed:
            continue
        if k in ("is_recurring", "is_regular"):
            updates[k] = 1 if v else 0
        elif k in ("recurrence_detail", "recurrence_exceptions") and isinstance(v, (dict, list)):
            updates[k] = json.dumps(v, ensure_ascii=False)
        elif k == "parent_id":
            updates[k] = int(v) if v else None
        else:
            updates[k] = v

    if "title" in updates and not str(updates["title"]).strip():
        return err("标题不能为空")
    if "status" in updates and updates["status"] not in VALID_STATUS:
        return err("无效状态")
    if "priority" in updates and updates["priority"] not in VALID_PRIORITY:
        return err("无效优先级")
    if updates.get("status") == "done" and "completed_at" not in data:
        updates["completed_at"] = now_str()
    if updates.get("status") in ("open", "in_progress", "pending_review"):
        updates["completed_at"] = None

    if not updates:
        return err("无更新字段")

    updates["updated_at"] = now_str()
    set_sql = ", ".join(f"{k} = ?" for k in updates)
    with get_conn() as conn:
        exists = conn.execute("SELECT id FROM items WHERE id = ?", [item_id]).fetchone()
        if not exists:
            return err("事项不存在", 404)
        conn.execute(f"UPDATE items SET {set_sql} WHERE id = ?", [*updates.values(), item_id])
    return ok(id=item_id)


@app.route("/api/items/<int:item_id>", methods=["DELETE"])
def api_item_delete(item_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM items WHERE id = ?", [item_id])
    return ok()


def _item_exists(conn, item_id: int) -> bool:
    return conn.execute("SELECT id FROM items WHERE id = ?", [item_id]).fetchone() is not None


def _attachment_row(conn, att_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM item_attachments WHERE id = ?", [att_id]).fetchone()
    return row_to_dict(row)


def _format_attachment(row: dict) -> dict:
    return {
        "id": row["id"],
        "item_id": row["item_id"],
        "original_filename": row["original_filename"],
        "mime_type": row.get("mime_type") or "",
        "size_bytes": row.get("size_bytes") or 0,
        "created_at": row.get("created_at") or "",
        "url": f"/api/attachments/{row['id']}/download",
    }


def _stored_filename(original: str) -> str:
    ext = Path(original).suffix.lower()
    if ext in BLOCKED_EXTENSIONS:
        ext = ".bin"
    safe_ext = secure_filename(ext) or ""
    if len(safe_ext) > 20:
        safe_ext = safe_ext[:20]
    return f"{uuid.uuid4().hex}{safe_ext}"


@app.route("/api/items/<int:item_id>/attachments", methods=["GET", "POST"])
def api_item_attachments(item_id: int):
    with get_conn() as conn:
        if not _item_exists(conn, item_id):
            return err("事项不存在", 404)

        if request.method == "GET":
            rows = rows_to_list(
                conn.execute(
                    "SELECT * FROM item_attachments WHERE item_id = ? ORDER BY created_at DESC",
                    [item_id],
                ).fetchall()
            )
            return ok(attachments=[_format_attachment(r) for r in rows])

        f = request.files.get("file")
        if not f or not f.filename:
            return err("请选择文件")
        original = f.filename.strip()
        if not original:
            return err("无效文件名")
        ext = Path(original).suffix.lower()
        if ext in BLOCKED_EXTENSIONS:
            return err("不支持该文件类型")

        data = f.read()
        if not data:
            return err("文件为空")
        if len(data) > MAX_ATTACHMENT_BYTES:
            return err(f"文件不能超过 {MAX_ATTACHMENT_BYTES // (1024 * 1024)}MB")

        stored = _stored_filename(original)
        item_dir = get_uploads_dir() / str(item_id)
        item_dir.mkdir(parents=True, exist_ok=True)
        (item_dir / stored).write_bytes(data)

        cur = conn.execute(
            """
            INSERT INTO item_attachments (item_id, original_filename, stored_filename, mime_type, size_bytes)
            VALUES (?, ?, ?, ?, ?)
            """,
            [item_id, original, stored, f.mimetype or "", len(data)],
        )
        row = _attachment_row(conn, cur.lastrowid)
    return ok(attachment=_format_attachment(row))


@app.route("/api/attachments/<int:att_id>/download", methods=["GET"])
def api_attachment_download(att_id: int):
    with get_conn() as conn:
        row = _attachment_row(conn, att_id)
        if not row:
            return err("附件不存在", 404)
        item_id = row["item_id"]
        stored = row["stored_filename"]
        original = row["original_filename"]

    path = get_uploads_dir() / str(item_id) / stored
    if not path.is_file():
        return err("文件已丢失", 404)
    return send_from_directory(path.parent, path.name, as_attachment=True, download_name=original)


@app.route("/api/attachments/<int:att_id>", methods=["DELETE"])
def api_attachment_delete(att_id: int):
    with get_conn() as conn:
        row = _attachment_row(conn, att_id)
        if not row:
            return err("附件不存在", 404)
        conn.execute("DELETE FROM item_attachments WHERE id = ?", [att_id])

    path = get_uploads_dir() / str(row["item_id"]) / row["stored_filename"]
    if path.is_file():
        path.unlink()
    return ok()


@app.route("/api/items/<int:item_id>/activities", methods=["POST"])
def api_item_activity(item_id: int):
    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()
    if not content:
        return err("内容不能为空")
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO activities (item_id, author_name, action, content) VALUES (?, ?, 'comment', ?)",
            [item_id, (data.get("author_name") or "").strip(), content],
        )
    return ok()


@app.route("/api/calendar")
def api_calendar():
    action = request.args.get("action", "month_events")
    scope = request.args.get("scope", "my")
    if scope not in VALID_SCOPE:
        scope = "my"
    team_name = request.args.get("team_name", "")
    dept_name = request.args.get("department_name", "")

    if action == "month_events":
        month = request.args.get("month", datetime.now().strftime("%Y-%m"))
        parent_id = int(request.args["parent_id"]) if request.args.get("parent_id") else None
        items = cal.get_month_events(scope, month, team_name, dept_name, parent_id)
        out = []
        for item in items:
            entry = enrich_item(item)
            entry["occurrences"] = item.get("occurrences")
            entry["frequency_label"] = item.get("frequency_label", "")
            out.append(entry)
        return ok(month=month, scope=scope, items=out)

    if action == "day_events":
        date_str = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))
        parent_id = int(request.args["parent_id"]) if request.args.get("parent_id") else None
        today_items = cal.get_day_events(scope, date_str, team_name, dept_name, parent_id)
        overdue_items = cal.get_overdue_items(scope, date_str, team_name, dept_name)
        today_items = [i for i in today_items if not i.get("is_regular") or i.get("show_due_to_checkpoint")]
        overdue_items = [i for i in overdue_items if not i.get("is_regular")]

        today = enrich_attachment_counts([format_day_item(i, date_str) for i in today_items])
        overdue = enrich_attachment_counts([format_day_item(i, date_str) for i in overdue_items])

        family = []
        if parent_id:
            family_rows = cal.get_parent_with_children(scope, parent_id, team_name, dept_name)
            for row in family_rows:
                if row.get("is_recurring") and row.get("recurrence_next_date"):
                    row["execution_date"] = row["recurrence_next_date"]
                else:
                    row["execution_date"] = row.get("start_date") or date_str
                row["frequency_label"] = cal.frequency_label(
                    row.get("frequency") or "", cal.parse_detail(row.get("recurrence_detail"))
                )
                family.append(format_day_item(row, date_str))

        return ok(date=date_str, scope=scope, today=today, overdue=overdue, family=family)

    if action == "regular_items":
        items = cal.get_regular_items(scope, team_name, dept_name)
        return ok(items=items)

    if action == "set_occurrence_status":
        if request.method != "POST":
            return err("Method not allowed", 405)
        data = request.get_json(silent=True) or {}
        item_id = int(data.get("item_id", 0))
        exec_date = (data.get("exec_date") or "").strip()
        new_status = (data.get("status") or "").strip()
        if item_id <= 0 or not exec_date or new_status not in {"open", "in_progress", "pending_review", "done"}:
            return err("参数错误")
        completed_at = now_str() if new_status == "done" else None
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO item_occurrences (item_id, exec_date, status, completed_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(item_id, exec_date) DO UPDATE SET
                    status = excluded.status,
                    completed_at = excluded.completed_at
                """,
                [item_id, exec_date, new_status, completed_at],
            )
        return ok(item_id=item_id, exec_date=exec_date, status=new_status)

    if action == "search_items":
        q = request.args.get("q", "").strip()
        if not q:
            return ok(items=[])
        like = f"%{q}%"
        scope_sql, scope_params = cal.build_scope_conditions(scope, team_name, dept_name)
        with get_conn() as conn:
            rows = conn.execute(
                f"""
                SELECT i.id, i.title, i.status, i.priority, i.is_recurring, i.frequency,
                       i.recurrence_detail, i.start_date, i.due_date, i.checkpoint_date, i.assignee_name
                FROM items i
                WHERE i.status != 'archived' AND (i.title LIKE ? OR i.content LIKE ?)
                  AND {scope_sql}
                ORDER BY i.updated_at DESC LIMIT 20
                """,
                [like, like, *scope_params],
            ).fetchall()
        items = []
        for r in rows:
            d = row_to_dict(r)
            d["frequency_label"] = ""
            if d.get("is_recurring") and d.get("frequency"):
                d["frequency_label"] = cal.frequency_label(d["frequency"], cal.parse_detail(d.get("recurrence_detail")))
            items.append(enrich_item(d))
        return ok(q=q, items=items)

    return err("未知 action", 400)


@app.route("/api/calendar/occurrence", methods=["POST"])
def api_occurrence():
    data = request.get_json(silent=True) or {}
    item_id = int(data.get("item_id", 0))
    exec_date = (data.get("exec_date") or "").strip()
    new_status = (data.get("status") or "").strip()
    if item_id <= 0 or not exec_date or new_status not in {"open", "in_progress", "pending_review", "done"}:
        return err("参数错误")
    completed_at = now_str() if new_status == "done" else None
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO item_occurrences (item_id, exec_date, status, completed_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(item_id, exec_date) DO UPDATE SET
                status = excluded.status,
                completed_at = excluded.completed_at
            """,
            [item_id, exec_date, new_status, completed_at],
        )
    return ok(item_id=item_id, exec_date=exec_date, status=new_status)


if __name__ == "__main__":
    from run import main
    main()
