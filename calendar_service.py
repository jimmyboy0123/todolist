"""日历服务：范围过滤、周期展开、日/月事件查询。"""
from __future__ import annotations

import calendar
import json
from datetime import date, datetime, timedelta

from db import get_conn, row_to_dict, rows_to_list

STATUS_MAP = {
    "draft": {"name": "草稿", "color": "#94a3b8"},
    "open": {"name": "待处理", "color": "#f97316"},
    "in_progress": {"name": "进行中", "color": "#3b82f6"},
    "pending_review": {"name": "待审核", "color": "#8b5cf6"},
    "done": {"name": "已完成", "color": "#22c55e"},
    "archived": {"name": "已归档", "color": "#94a3b8"},
}

PRIORITY_MAP = {
    "urgent": {"name": "紧急", "color": "#ef4444", "icon": "🔴"},
    "high": {"name": "高", "color": "#f97316", "icon": "🟠"},
    "normal": {"name": "普通", "color": "#3b82f6", "icon": "🔵"},
    "low": {"name": "低", "color": "#94a3b8", "icon": "⚪"},
}

FREQ_LABELS = {
    "daily": "每天",
    "weekly": "每周",
    "monthly": "每月",
    "quarterly": "每季度",
    "semi_annual": "每半年",
    "yearly": "每年",
    "custom": "自定义",
}


def parse_detail(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def frequency_label(freq: str, detail: dict | None = None) -> str:
    detail = detail or {}
    label = FREQ_LABELS.get(freq, freq)
    if freq == "custom" and detail.get("interval_days"):
        label = f"每 {int(detail['interval_days'])} 天"
    if freq == "weekly" and detail.get("day_of_week"):
        names = ["", "一", "二", "三", "四", "五", "六", "日"]
        days = [f"周{names[int(d)]}" for d in detail["day_of_week"] if 1 <= int(d) <= 7]
        if days:
            label += f"（{'、'.join(days)}）"
    return label


def nth_weekday_of_month(year: int, month: int, nth: int, dow: int) -> str | None:
    first = date(year, month, 1)
    first_dow = first.isoweekday()
    diff = (dow - first_dow + 7) % 7
    first_day = 1 + diff
    days_in = calendar.monthrange(year, month)[1]
    if nth == 5:
        day = first_day
        while day + 7 <= days_in:
            day += 7
        return date(year, month, day).isoformat()
    day = first_day + (nth - 1) * 7
    if day > days_in:
        return None
    return date(year, month, day).isoformat()


def expand_recurrence_in_range(item: dict, range_start: str, range_end: str) -> list[str]:
    frequency = item.get("frequency") or ""
    if not frequency:
        return []

    detail = parse_detail(item.get("recurrence_detail"))
    item_start = item.get("start_date") or range_start
    next_date = item.get("recurrence_next_date")
    if next_date and next_date < item_start:
        item_start = next_date

    is_recurring = bool(item.get("is_recurring"))
    status = item.get("status") or ""
    closed = status == "archived" or (not is_recurring and status == "done")
    if closed and item.get("completed_at"):
        item_end = item["completed_at"][:10]
    elif item.get("due_date") and item["due_date"] != "2999-12-31":
        item_end = item["due_date"]
    else:
        item_end = range_end

    gen_start = max(item_start, range_start)
    gen_end = min(item_end, range_end)
    if gen_start > gen_end:
        return []

    adjust = detail.get("holiday_adjust", "none")
    gs = date.fromisoformat(gen_start)
    ge = date.fromisoformat(gen_end)
    if adjust != "none":
        gs = gs - timedelta(days=2)
        ge = ge + timedelta(days=2)

    is_ts = date.fromisoformat(item_start)
    occurrences: list[str] = []

    if frequency == "daily":
        cur = gs
        while cur <= ge:
            occurrences.append(cur.isoformat())
            cur += timedelta(days=1)

    elif frequency == "weekly":
        if detail.get("day_of_week"):
            targets = {int(d) for d in detail["day_of_week"]}
            cur = gs
            while cur <= ge:
                if cur.isoweekday() in targets:
                    occurrences.append(cur.isoformat())
                cur += timedelta(days=1)
        else:
            cur = is_ts
            while cur < gs:
                cur += timedelta(days=7)
            while cur <= ge:
                occurrences.append(cur.isoformat())
                cur += timedelta(days=7)

    elif frequency == "monthly":
        if detail.get("monthly_mode") == "week" and detail.get("week_of_month") and detail.get("week_day"):
            nth = int(detail["week_of_month"])
            dow = int(detail["week_day"])
            y, m = gs.year, gs.month
            for _ in range(24):
                ds = nth_weekday_of_month(y, m, nth, dow)
                if ds:
                    d = date.fromisoformat(ds)
                    if gs <= d <= ge and d >= is_ts:
                        occurrences.append(ds)
                m += 1
                if m > 12:
                    m = 1
                    y += 1
                if date(y, m, 1) > ge:
                    break
        else:
            target_day = int(detail.get("day_of_month") or is_ts.day)
            y, m = gs.year, gs.month
            for _ in range(24):
                dim = calendar.monthrange(y, m)[1]
                day = min(target_day, dim)
                ds = date(y, m, day).isoformat()
                d = date.fromisoformat(ds)
                if gs <= d <= ge and d >= is_ts:
                    occurrences.append(ds)
                m += 1
                if m > 12:
                    m = 1
                    y += 1
                if date(y, m, 1) > ge:
                    break

    elif frequency == "quarterly":
        qi = int(detail.get("quarter_index") or 0)
        qd = int(detail.get("day_of_month") or 0)
        if 1 <= qi <= 3 and 1 <= qd <= 31:
            months = [qi, qi + 3, qi + 6, qi + 9]
            for y in range(gs.year, ge.year + 1):
                for tm in months:
                    dim = calendar.monthrange(y, tm)[1]
                    ds = date(y, tm, min(qd, dim)).isoformat()
                    d = date.fromisoformat(ds)
                    if gs <= d <= ge and d >= is_ts:
                        occurrences.append(ds)
        else:
            cur = is_ts
            while cur < gs:
                cur = _add_months(cur, 3)
            while cur <= ge:
                occurrences.append(cur.isoformat())
                cur = _add_months(cur, 3)

    elif frequency == "semi_annual":
        cur = is_ts
        while cur < gs:
            cur = _add_months(cur, 6)
        while cur <= ge:
            occurrences.append(cur.isoformat())
            cur = _add_months(cur, 6)

    elif frequency == "yearly":
        tm = int(detail.get("month") or is_ts.month)
        td = int(detail.get("day_of_month") or is_ts.day)
        for y in range(gs.year, ge.year + 1):
            try:
                d = date(y, tm, td)
            except ValueError:
                continue
            if gs <= d <= ge and d >= is_ts:
                occurrences.append(d.isoformat())

    elif frequency == "custom":
        interval = max(1, int(detail.get("interval_days") or 1))
        cur = is_ts
        while cur < gs:
            cur += timedelta(days=interval)
        while cur <= ge:
            occurrences.append(cur.isoformat())
            cur += timedelta(days=interval)

    occurrences = sorted(set(occurrences))

    if adjust != "none":
        adjusted = []
        for ds in occurrences:
            d = date.fromisoformat(ds)
            dow = d.isoweekday()
            if dow == 6:
                d = d + timedelta(days=2 if adjust == "next" else -1)
            elif dow == 7:
                d = d + timedelta(days=1 if adjust == "next" else -2)
            adjusted.append(d.isoformat())
        occurrences = sorted(set(adjusted))

    exceptions = parse_detail(item.get("recurrence_exceptions"))
    if isinstance(exceptions, dict) and exceptions:
        occurrences = [d for d in occurrences if d not in exceptions]
        for new_date in exceptions.values():
            if new_date and range_start <= new_date <= range_end:
                occurrences.append(new_date)
        occurrences = sorted(set(occurrences))

    return [d for d in occurrences if range_start <= d <= range_end]


def _add_months(d: date, months: int) -> date:
    m = d.month - 1 + months
    y = d.year + m // 12
    m = m % 12 + 1
    dim = calendar.monthrange(y, m)[1]
    return date(y, m, min(d.day, dim))


def month_range(year_month: str) -> tuple[str, str]:
    y, m = map(int, year_month.split("-"))
    start = date(y, m, 1).isoformat()
    end = date(y, m, calendar.monthrange(y, m)[1]).isoformat()
    return start, end


def build_scope_conditions(scope: str, team_name: str = "", dept_name: str = "") -> tuple[str, list]:
    where: list[str] = []
    params: list = []

    if scope == "team":
        where.append("i.scope = 'team'")
        if team_name:
            where.append("i.team_name = ?")
            params.append(team_name)
    elif scope == "department":
        where.append("i.scope = 'department'")
        if dept_name:
            where.append("i.department_name = ?")
            params.append(dept_name)
    elif scope == "company":
        where.append("i.scope = 'company'")
    else:
        where.append("i.scope = 'my'")

    return " AND ".join(where) if where else "1=1", params


def build_query(scope: str, start_date: str, end_date: str, day_only: bool = False,
                parent_id: int | None = None, team_name: str = "", dept_name: str = "") -> tuple[str, list]:
    where = ["i.status != ?", "(i.start_date IS NOT NULL OR i.due_date IS NOT NULL OR i.checkpoint_date IS NOT NULL)"]
    params: list = ["archived"]

    if parent_id is not None:
        where.append("(i.id = ? OR i.parent_id = ?)")
        params.extend([parent_id, parent_id])

    if day_only:
        where.append(
            "(((i.is_recurring = 0 AND (i.start_date = ? OR i.due_date = ? OR i.checkpoint_date = ?))"
            " OR (i.is_recurring = 1 AND (i.start_date IS NULL OR i.start_date <= ?)"
            "     AND (i.due_date IS NULL OR i.due_date >= ? OR i.due_date = '2999-12-31')))"
            " OR (i.checkpoint_date = ?))"
        )
        params.extend([start_date, start_date, start_date, end_date, start_date, start_date])
    else:
        where.append("(i.start_date IS NULL OR i.start_date <= ?)")
        params.append(end_date)
        where.append("(i.is_recurring = 1 OR i.due_date IS NULL OR i.due_date >= ?)")
        params.append(start_date)

    scope_sql, scope_params = build_scope_conditions(scope, team_name, dept_name)
    where.append(scope_sql)
    params.extend(scope_params)
    return " AND ".join(where), params


def _child_count_sql() -> str:
    return "(SELECT COUNT(*) FROM items c WHERE c.parent_id = i.id) AS child_count"


def fetch_events(scope: str, start_date: str, end_date: str, with_detail: bool = False,
                 day_only: bool = False, parent_id: int | None = None,
                 team_name: str = "", dept_name: str = "") -> list[dict]:
    where_sql, params = build_query(scope, start_date, end_date, day_only, parent_id, team_name, dept_name)
    child_sql = _child_count_sql()

    if with_detail:
        sql = f"""
            SELECT i.*, {child_sql},
                   t.type_name, t.icon AS type_icon, t.color AS type_color
            FROM items i
            LEFT JOIN item_types t ON t.type_key = i.item_type
            WHERE {where_sql}
            ORDER BY CASE i.priority WHEN 'urgent' THEN 1 WHEN 'high' THEN 2 WHEN 'normal' THEN 3 ELSE 4 END,
                     i.due_date ASC, i.created_at DESC
        """
    else:
        sql = f"""
            SELECT i.id, i.title, i.item_type, i.status, i.priority,
                   i.start_date, i.due_date, i.completed_at,
                   i.is_recurring, i.frequency, i.recurrence_detail, i.recurrence_exceptions,
                   i.checkpoint_date, i.parent_id, i.is_regular, {child_sql}
            FROM items i
            WHERE {where_sql}
            ORDER BY i.due_date ASC
        """

    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()

    result: list[dict] = []
    for row in rows:
        item = row_to_dict(row)
        if item.get("is_recurring"):
            occurrences = expand_recurrence_in_range(item, start_date, end_date)
            if not occurrences:
                continue
            if with_detail:
                for exec_date in occurrences:
                    entry = dict(item)
                    entry["execution_date"] = exec_date
                    entry["is_start"] = item.get("start_date") == exec_date
                    entry["show_due_to_checkpoint"] = bool(
                        item.get("checkpoint_date") and item["checkpoint_date"] == exec_date
                    )
                    entry["frequency_label"] = frequency_label(item.get("frequency", ""), parse_detail(item.get("recurrence_detail")))
                    result.append(entry)
            else:
                item["occurrences"] = occurrences
                item["frequency_label"] = frequency_label(item.get("frequency", ""), parse_detail(item.get("recurrence_detail")))
                result.append(item)
        else:
            if with_detail:
                item["execution_date"] = ""
                item["is_start"] = item.get("start_date") == start_date
                item["show_due_to_checkpoint"] = bool(
                    item.get("checkpoint_date") and item["checkpoint_date"] == start_date
                )
                item["frequency_label"] = ""
            item["occurrences"] = None
            item["frequency_label"] = ""
            result.append(item)

    if day_only and with_detail:
        rec_ids = [int(r["id"]) for r in result if r.get("is_recurring")]
        if rec_ids:
            placeholders = ",".join("?" * len(rec_ids))
            with get_conn() as conn:
                occ_rows = conn.execute(
                    f"SELECT item_id, status, completed_at FROM item_occurrences WHERE exec_date = ? AND item_id IN ({placeholders})",
                    [start_date, *rec_ids],
                ).fetchall()
            occ_map = {int(r["item_id"]): dict(r) for r in occ_rows}
            for r in result:
                if r.get("is_recurring"):
                    iid = int(r["id"])
                    if iid in occ_map:
                        r["occurrence_status"] = occ_map[iid]["status"]
                        r["occurrence_completed_at"] = occ_map[iid]["completed_at"]

    return result


def get_month_events(scope: str, year_month: str, team_name: str = "", dept_name: str = "",
                     parent_id: int | None = None) -> list[dict]:
    start, end = month_range(year_month)
    return fetch_events(scope, start, end, False, False, parent_id, team_name, dept_name)


def get_day_events(scope: str, date_str: str, team_name: str = "", dept_name: str = "",
                   parent_id: int | None = None) -> list[dict]:
    return fetch_events(scope, date_str, date_str, True, True, parent_id, team_name, dept_name)


def get_overdue_items(scope: str, date_str: str, team_name: str = "", dept_name: str = "") -> list[dict]:
    scope_sql, scope_params = build_scope_conditions(scope, team_name, dept_name)
    sql = f"""
        SELECT i.*, t.type_name, t.icon AS type_icon, t.color AS type_color
        FROM items i
        LEFT JOIN item_types t ON t.type_key = i.item_type
        WHERE i.status IN ('open','in_progress','pending_review')
          AND i.due_date IS NOT NULL AND i.due_date != '2999-12-31' AND i.due_date < ?
          AND {scope_sql}
        ORDER BY i.due_date ASC
    """
    with get_conn() as conn:
        return rows_to_list(conn.execute(sql, [date_str, *scope_params]).fetchall())


def get_regular_items(scope: str, team_name: str = "", dept_name: str = "") -> list[dict]:
    scope_sql, scope_params = build_scope_conditions(scope, team_name, dept_name)
    sql = f"""
        SELECT i.id, i.title, i.parent_id
        FROM items i
        WHERE i.is_regular = 1 AND i.status NOT IN ('done','archived') AND {scope_sql}
        ORDER BY i.parent_id ASC, i.start_date ASC, i.created_at ASC
    """
    with get_conn() as conn:
        rows = rows_to_list(conn.execute(sql, scope_params).fetchall())
    for r in rows:
        r["parent_id"] = int(r["parent_id"]) if r.get("parent_id") else None
    return rows


def get_parent_with_children(scope: str, parent_id: int, team_name: str = "", dept_name: str = "") -> list[dict]:
    scope_sql, scope_params = build_scope_conditions(scope, team_name, dept_name)
    child_sql = _child_count_sql()
    sql = f"""
        SELECT i.*, {child_sql}, t.type_name, t.icon AS type_icon, t.color AS type_color
        FROM items i
        LEFT JOIN item_types t ON t.type_key = i.item_type
        WHERE (i.id = ? OR i.parent_id = ?) AND i.status != 'archived' AND {scope_sql}
        ORDER BY i.parent_id ASC, i.created_at ASC
    """
    with get_conn() as conn:
        return rows_to_list(conn.execute(sql, [parent_id, parent_id, *scope_params]).fetchall())
