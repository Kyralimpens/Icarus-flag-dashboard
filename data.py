"""Live data layer for the Operations Check-in dashboard.
Reads DB credentials from environment variables (set them in Railway), queries the
Icarus MariaDB for store health + client churn. Read-only SELECTs. Short TTL cache."""
import os, time, datetime
import pymysql
from collections import defaultdict

SPEND_TARGET = 1000.0
WINDOW = 14
EXCLUDE_HEALTH_BUYERS = {"Henk-Jan van Steeg"}
CACHE_TTL = int(os.environ.get("CACHE_TTL_SECONDS", "600"))  # 10 min default

_cache = {"t": 0, "payload": None}


def _connect():
    return pymysql.connect(
        host=os.environ["DB_HOST"], port=int(os.environ.get("DB_PORT", "3306")),
        user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_DATABASE"], connect_timeout=15,
        cursorclass=pymysql.cursors.DictCursor, read_timeout=30,
    )


def _months_this_year(today):
    return ["%d-%02d" % (today.year, m) for m in range(1, today.month + 1)]


def _fmt_date(d):
    return d.strftime("%d %b %Y") if d else "—"


def _months_between(start, end):
    m = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        m -= 1
    return m


def get_health(cur, today):
    win_start = today - datetime.timedelta(days=WINDOW)
    win7_start = today - datetime.timedelta(days=7)
    cur.execute(
        """
        SELECT s.id, s.name, s.onboarding_date,
               COALESCE(e.name, CONCAT(e.first_name,' ',e.last_name)) AS buyer
        FROM store s LEFT JOIN employee e ON e.id = s.employee_id
        WHERE s.status = 'Active'
        """
    )
    stores = {r["id"]: r for r in cur.fetchall()}
    cur.execute(
        """
        SELECT store_id,
               SUM(CASE WHEN date > %s THEN ad_spend_in_euro ELSE 0 END) AS spend14,
               SUM(CASE WHEN date > %s THEN ad_spend_in_euro ELSE 0 END) AS spend7
        FROM v_store_performance WHERE date > %s GROUP BY store_id
        """,
        (win_start, win7_start, win_start),
    )
    spend = {r["store_id"]: r for r in cur.fetchall()}
    rows = []
    for sid, s in stores.items():
        buyer = s["buyer"] or "— unassigned —"
        if buyer in EXCLUDE_HEALTH_BUYERS:
            continue
        ob = s["onboarding_date"]
        mo = _months_between(ob, today) if ob else None
        sp = spend.get(sid, {})
        avg14 = float(sp.get("spend14") or 0) / WINDOW
        avg7 = float(sp.get("spend7") or 0) / 7
        if avg14 < 50:            # drop stores with no recent ad spend
            continue
        if mo is None:
            cls = "unknown"
        elif mo < 3:
            cls = "ramp"
        elif avg14 >= SPEND_TARGET:
            cls = "ontarget"
        else:
            cls = "buddy"
        rows.append({"buyer": buyer, "name": s["name"], "onboarding": _fmt_date(ob),
                     "months": mo, "avg14": avg14, "avg7": avg7, "cls": cls,
                     "running": True})
    tot = {"ontarget": 0, "buddy": 0, "ramp": 0, "unknown": 0}
    for r in rows:
        tot[r["cls"]] += 1
    return {"today": today.strftime("%d %b %Y"), "target": SPEND_TARGET,
            "window": WINDOW, "totals": tot, "count": len(rows), "rows": rows}


def get_churn(cur, today):
    start = "%d-01-01" % today.year
    end = (today + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    cur.execute(
        """
        SELECT mal.name, mal.date, DATE_FORMAT(mal.date,'%%Y-%%m') ym,
               (SELECT COALESCE(e.name, CONCAT(e.first_name,' ',e.last_name))
                  FROM client c JOIN store s ON s.client_id = c.id
                  LEFT JOIN employee e ON e.id = s.employee_id
                 WHERE c.monday_id = mal.client_monday_id
                 ORDER BY s.onboarding_date DESC, s.created_at DESC LIMIT 1) AS buyer
        FROM monday_activity_log mal
        WHERE mal.type='Churned Client' AND mal.date >= %s AND mal.date < %s
        ORDER BY mal.date
        """,
        (start, end),
    )
    seen = set()
    churn = defaultdict(lambda: defaultdict(int))
    for r in cur.fetchall():
        k = (r["name"].strip().lower(), r["date"])   # dedupe by client + date
        if k in seen:
            continue
        seen.add(k)
        churn[r["buyer"] or "— unattributed —"][r["ym"]] += 1
    months = _months_this_year(today)
    return {"months": months, "today": today.strftime("%d %b %Y"),
            "churn": {b: {m: churn[b].get(m, 0) for m in months} for b in churn}}


def get_data(force=False):
    now = time.time()
    if not force and _cache["payload"] and now - _cache["t"] < CACHE_TTL:
        return _cache["payload"]
    today = datetime.date.today()
    conn = _connect()
    try:
        with conn.cursor() as cur:
            payload = {"health": get_health(cur, today), "churn": get_churn(cur, today),
                       "generated_at": datetime.datetime.now().strftime("%d %b %Y %H:%M")}
    finally:
        conn.close()
    _cache.update(t=now, payload=payload)
    return payload
