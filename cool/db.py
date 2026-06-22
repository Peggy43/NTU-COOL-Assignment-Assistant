import json
import sqlite3

def init_db():
    conn = sqlite3.connect("data/assignment.db")
    cursor = conn.cursor()
    # cursor.execute("DROP TABLE IF EXISTS assignments")
    cursor.execute("""
    CREATE TABLE if not exists assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assignment_id INTEGER UNIQUE,
    course_id INTEGER,
    course_name TEXT,
    assignment_name TEXT,
    start_date TEXT,
    due_date TEXT,
    soft_deadline TEXT,
    status TEXT,
    source TEXT,
    submitted INTEGER DEFAULT 0
    )
    """)
    print("assignments created")
    # cursor.execute("DROP TABLE IF EXISTS focus_log")
    cursor.execute("""
    CREATE TABLE if not exists focus_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        assignment_id INTEGER NOT NULL,

        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,

        duration INTEGER NOT NULL,

        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    print("focus_log created")

    conn.commit()
    conn.close()


def seed_courses():
    with open("data/assignments.json", "r", encoding="utf-8") as f:
        assignments = json.load(f)

    conn = sqlite3.connect("data/assignment.db")
    cursor = conn.cursor()

    for a in assignments:

        cursor.execute("""
        INSERT OR IGNORE INTO assignments (
            course_id,
            course_name,

            assignment_id,
            assignment_name,

            due_date,
            start_date,
            soft_deadline,

            status,

            source,
            submitted
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            a["course_id"],
            a["course_name"],
            
            a["assignment_id"],
            a["assignment_name"],

            a["due_date"],
            a["start_date"],
            a["soft_deadline"],

            a["status"],

            a["source"],
            a["submitted"]
        ))

    conn.commit()
    conn.close()

    print("匯入完成")