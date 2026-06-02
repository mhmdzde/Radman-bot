"""
database.py — راه‌اندازی SQLite و توابع CRUD
"""
import sqlite3
from datetime import datetime

DB_PATH = "ev_project.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS statuses (
        id      INTEGER PRIMARY KEY,
        name    TEXT NOT NULL UNIQUE,
        emoji   TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS members (
        id      INTEGER PRIMARY KEY,
        name    TEXT NOT NULL,
        role    TEXT NOT NULL,
        tg_id   INTEGER UNIQUE
    );

    CREATE TABLE IF NOT EXISTS phases (
        id          INTEGER PRIMARY KEY,
        name        TEXT NOT NULL,
        period      TEXT,
        budget_usd  REAL
    );

    CREATE TABLE IF NOT EXISTS tasks (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        title       TEXT NOT NULL,
        member_id   INTEGER REFERENCES members(id),   -- NULL یعنی تسک تیمی
        phase_id    INTEGER REFERENCES phases(id),
        status_id   INTEGER REFERENCES statuses(id) DEFAULT 1,
        deadline    TEXT,
        completed   TEXT,
        notes       TEXT,
        doc_link    TEXT,
        created_at  TEXT DEFAULT (datetime('now','localtime'))
    );

    -- جدول واسط برای تسک‌های تیمی (چند مسئول)
    CREATE TABLE IF NOT EXISTS task_members (
        task_id   INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
        member_id INTEGER REFERENCES members(id) ON DELETE CASCADE,
        PRIMARY KEY (task_id, member_id)
    );

    CREATE TABLE IF NOT EXISTS meetings (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        date        TEXT,
        summary     TEXT,
        decisions   TEXT,
        responsible TEXT,
        deadline    TEXT,
        created_at  TEXT DEFAULT (datetime('now','localtime'))
    );
    """)

    # ── وضعیت‌ها ──
    if not c.execute("SELECT 1 FROM statuses LIMIT 1").fetchone():
        c.executemany("INSERT INTO statuses (id, name, emoji) VALUES (?,?,?)", [
            (1, "باز",        "🟡"),
            (2, "در جریان",   "🔵"),
            (3, "انجام شده",  "✅"),
            (4, "معلق",       "⏸"),
            (5, "فوری",       "🔴"),
        ])

    # ── اعضا ──
    if not c.execute("SELECT 1 FROM members LIMIT 1").fetchone():
        c.executemany("INSERT INTO members (id, name, role) VALUES (?,?,?)", [
            (1, "علیرضا علی‌حسینی",   "سرمایه‌گذار"),
            (2, "محمد محمدزاده مزار", "مدیر فنی"),
            (3, "علی نوعی",           "مدیر عامل"),
            (4, "علی حیدری",          "مدیر بازرگانی"),
        ])

    # ── فازها ──
    if not c.execute("SELECT 1 FROM phases LIMIT 1").fetchone():
        c.executemany("INSERT INTO phases (name, period, budget_usd) VALUES (?,?,?)", [
            ("فاز ۱", "خرداد – شهریور ۱۴۰۵", 10555),
            ("فاز ۲", "شهریور – آذر ۱۴۰۵",   5450),
            ("فاز ۳", "آذر – اسفند ۱۴۰۵",    8666),
            ("فاز ۴", "اسفند ۱۴۰۵ – خرداد ۱۴۰۶", 8223),
        ])

    # ── تسک‌ها (کامل از اکسل) ──
    # member_id=None یعنی تسک تیمیه — بعداً توی task_members ثبت می‌شه
    # status_id: 1=باز، 2=در جریان، 3=انجام شده، 4=معلق، 5=فوری
    if not c.execute("SELECT 1 FROM tasks LIMIT 1").fetchone():
        seed_tasks = [
            # (title,                                           member_id, phase_id, status_id, deadline)
            ("امضای اقرارنامه محضری",                           None, 1, 5, None),           # 1 — تیم، فوری
            ("پرداخت سرمایه فاز اول — ۱۰,۵۵۵ دلار",            1,    1, 2, "خرداد ۱۴۰۵"),   # 2 — در جریان
            ("راه‌اندازی وبسایت رسمی شرکت",                     2,    1, 1, None),           # 3
            ("اجاره دفتر اداری و تجهیزات",                      3,    1, 1, None),           # 4
            ("ایجاد حداقل ۱۰ سرنخ فروش",                        4,    1, 1, None),           # 5
            ("واردات نمونه اولیه شارژر",                         4,    1, 1, None),           # 6
            ("تهیه گزارش تحلیل بازار",                           4,    1, 1, None),           # 7
            ("تهیه مستندات فنی اولیه",                           2,    1, 1, None),           # 8
            ("ارائه گزارش فعالیت بازاریابی",                     4,    1, 1, None),           # 9
            ("تنظیم گزارش مالی ماهانه",                          3,    1, 1, None),           # 10
            ("پرداخت سرمایه فاز دوم — ۵,۴۵۰ دلار",              1,    2, 1, "شهریور ۱۴۰۵"),  # 11
            ("انجام حداقل ۳ مذاکره رسمی تجاری",                  4,    2, 1, None),           # 12
            ("توسعه نمونه اولیه باکس و شارژر",                   2,    2, 1, None),           # 13
            ("تهیه مستندات فنی ارتباطات و تجهیزات",              2,    2, 1, None),           # 14
            ("آماده‌سازی پروتوتایپ اولیه",                       2,    2, 1, None),           # 15
            ("انعقاد حداقل ۱ قرارداد فروش",                      3,    2, 1, None),           # 16
            ("تکمیل ساختار فنی اولیه محصول",                     2,    2, 1, None),           # 17
            ("پرداخت سرمایه فاز سوم — ۸,۶۶۶ دلار",              1,    3, 1, "آذر ۱۴۰۵"),     # 18
            ("انعقاد حداقل ۲ قرارداد رسمی فروش",                 3,    3, 1, None),           # 19
            ("دریافت پیش‌پرداخت از مشتریان",                     4,    3, 1, None),           # 20
            ("فروش حداقل ۱۵ دستگاه شارژر",                       4,    3, 1, None),           # 21
            ("ایجاد جریان نقدی عملیاتی",                         3,    3, 1, None),           # 22
            ("مستندسازی پروژه‌های اجراشده",                      2,    3, 1, None),           # 23
            ("پرداخت سرمایه فاز چهارم — ۸,۲۲۳ دلار",            1,    4, 1, "اسفند ۱۴۰۵"),  # 24
            ("فروش حداقل ۳۰ دستگاه شارژر و باکس",                4,    4, 1, None),           # 25
            ("واردات حداقل ۳۰ دستگاه شارژر",                     3,    4, 1, None),           # 26
            ("ایجاد ساختار خدمات پس از فروش",                    3,    4, 1, None),           # 27
            ("توسعه تیم فروش",                                   4,    4, 1, None),           # 28
            ("آماده‌سازی تیم خدمات و پشتیبانی",                  3,    4, 1, None),           # 29
            ("ارائه گزارش نصب و بهره‌برداری",                    2,    4, 1, None),           # 30
        ]
        for row in seed_tasks:
            title, member_id, phase_id, status_id, deadline = row
            cur = c.execute(
                "INSERT INTO tasks (title, member_id, phase_id, status_id, deadline) VALUES (?,?,?,?,?)",
                (title, member_id, phase_id, status_id, deadline)
            )
            task_id = cur.lastrowid
            # تسک ۱ — تیمی: همه اعضا مسئولند
            if member_id is None:
                for mid in [1, 2, 3, 4]:
                    c.execute("INSERT INTO task_members VALUES (?,?)", (task_id, mid))

    conn.commit()
    conn.close()


# ─── توابع خواندن ───────────────────────────────────────────────

def get_statuses():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM statuses ORDER BY id").fetchall()
    conn.close()
    return rows


def get_tasks(member_id=None, phase_id=None, status_id=None):
    conn = get_conn()
    q = """
        SELECT t.id, t.title, t.deadline, t.notes, t.doc_link,
               s.name AS status, s.emoji AS status_emoji,
               COALESCE(m.name, 'تیم') AS member_name,
               COALESCE(m.role, '—')   AS role,
               p.name AS phase_name
        FROM tasks t
        JOIN statuses s ON t.status_id = s.id
        LEFT JOIN members m ON t.member_id = m.id
        JOIN phases  p ON t.phase_id = p.id
        WHERE 1=1
    """
    params = []
    if member_id:
        # تسک‌های مستقیم + تسک‌های تیمی که عضو توشون هست
        q += """
            AND (t.member_id = ?
                 OR t.id IN (SELECT task_id FROM task_members WHERE member_id = ?))
        """
        params += [member_id, member_id]
    if phase_id:
        q += " AND t.phase_id=?"; params.append(phase_id)
    if status_id:
        q += " AND t.status_id=?"; params.append(status_id)
    q += " ORDER BY t.phase_id, t.id"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return rows


def get_task(task_id):
    conn = get_conn()
    row = conn.execute("""
        SELECT t.*,
               s.name AS status, s.emoji AS status_emoji,
               COALESCE(m.name, 'تیم') AS member_name,
               COALESCE(m.role, '—')   AS role,
               p.name AS phase_name
        FROM tasks t
        JOIN statuses s ON t.status_id = s.id
        LEFT JOIN members m ON t.member_id = m.id
        JOIN phases  p ON t.phase_id = p.id
        WHERE t.id=?
    """, (task_id,)).fetchone()

    # اگه تسک تیمی بود، لیست اعضا رو هم برگردون
    team_members = []
    if row and row["member_id"] is None:
        team_members = conn.execute("""
            SELECT m.name, m.role FROM task_members tm
            JOIN members m ON tm.member_id = m.id
            WHERE tm.task_id = ?
        """, (task_id,)).fetchall()

    conn.close()
    return row, team_members


def get_members():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM members ORDER BY id").fetchall()
    conn.close()
    return rows


def get_phases():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM phases ORDER BY id").fetchall()
    conn.close()
    return rows


def get_dashboard():
    conn = get_conn()
    stats = {}

    stats["total"] = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]

    for row in conn.execute("SELECT name, COUNT(t.id) FROM statuses s LEFT JOIN tasks t ON t.status_id=s.id GROUP BY s.id"):
        stats[row[0]] = row[1]

    stats["phases"] = conn.execute("""
        SELECT p.name, p.budget_usd,
               COUNT(t.id) AS total,
               SUM(t.status_id=3) AS done,
               SUM(t.status_id=1) AS open,
               SUM(t.status_id=2) AS inprogress,
               SUM(t.status_id=4) AS pending,
               SUM(t.status_id=5) AS urgent
        FROM phases p LEFT JOIN tasks t ON p.id=t.phase_id
        GROUP BY p.id ORDER BY p.id
    """).fetchall()

    stats["members"] = conn.execute("""
        SELECT m.name, m.role,
               COUNT(t.id) AS total,
               SUM(t.status_id=3) AS done,
               SUM(t.status_id=1) AS open,
               SUM(t.status_id=2) AS inprogress,
               SUM(t.status_id=4) AS pending,
               SUM(t.status_id=5) AS urgent
        FROM members m
        LEFT JOIN tasks t ON m.id=t.member_id
        GROUP BY m.id ORDER BY m.id
    """).fetchall()

    conn.close()
    return stats


# ─── توابع نوشتن ────────────────────────────────────────────────

def update_task_status(task_id, status_id: int):
    conn = get_conn()
    completed = datetime.now().strftime("%Y-%m-%d") if status_id == 3 else None
    conn.execute(
        "UPDATE tasks SET status_id=?, completed=? WHERE id=?",
        (status_id, completed, task_id)
    )
    conn.commit()
    conn.close()


def add_task(title, member_id, phase_id, status_id=1, deadline=None, notes=None, team=False):
    """
    اگه team=True باشه، member_id رو نادیده می‌گیره و یه تسک تیمی می‌سازه.
    در غیر این‌صورت member_id مسئول مستقیمه.
    """
    conn = get_conn()
    actual_member = None if team else member_id
    cur = conn.execute(
        "INSERT INTO tasks (title, member_id, phase_id, status_id, deadline, notes) VALUES (?,?,?,?,?,?)",
        (title, actual_member, phase_id, status_id, deadline, notes)
    )
    task_id = cur.lastrowid
    if team:
        for mid in [1, 2, 3, 4]:
            conn.execute("INSERT INTO task_members VALUES (?,?)", (task_id, mid))
    conn.commit()
    conn.close()
    return task_id


def update_task_notes(task_id, notes):
    conn = get_conn()
    conn.execute("UPDATE tasks SET notes=? WHERE id=?", (notes, task_id))
    conn.commit()
    conn.close()


def update_task_doc(task_id, doc_link):
    conn = get_conn()
    conn.execute("UPDATE tasks SET doc_link=? WHERE id=?", (doc_link, task_id))
    conn.commit()
    conn.close()


def delete_task(task_id):
    conn = get_conn()
    conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()
