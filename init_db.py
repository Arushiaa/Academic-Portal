"""Create / upgrade academic.db.

Safe to run repeatedly:
  * fresh database  -> creates everything and inserts sample data
  * old database    -> backs it up, rebuilds tables with the new schema and
                       keeps your existing students, registrations and grades
                       (plain-text passwords are converted to hashes)
"""
import os
import shutil
import sqlite3
from werkzeug.security import generate_password_hash

from database import DB_PATH, get_db

SCHEMA = """
CREATE TABLE IF NOT EXISTS students(
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    name TEXT NOT NULL,
    roll_number TEXT,
    programme TEXT,
    department TEXT,
    academic_status TEXT DEFAULT 'Active',
    semester INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS instructors(
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    name TEXT NOT NULL,
    department TEXT
);
CREATE TABLE IF NOT EXISTS courses(
    course_id TEXT PRIMARY KEY,
    course_name TEXT NOT NULL,
    credits INTEGER NOT NULL,
    instructor_id INTEGER REFERENCES instructors(id),
    capacity INTEGER NOT NULL DEFAULT 60
);
CREATE TABLE IF NOT EXISTS registrations(
    student_id INTEGER NOT NULL REFERENCES students(id),
    course_id TEXT NOT NULL REFERENCES courses(course_id),
    PRIMARY KEY(student_id, course_id)
);
CREATE TABLE IF NOT EXISTS grades(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id),
    course_id TEXT NOT NULL REFERENCES courses(course_id),
    semester INTEGER NOT NULL,
    grade TEXT NOT NULL,
    UNIQUE(student_id, course_id, semester)   -- allows repeating a course in a later semester
);
"""

TABLES = ["students", "instructors", "courses", "registrations", "grades"]


def _hash(pw):
    return pw if pw.startswith(("pbkdf2:", "scrypt:")) else generate_password_hash(pw)


def _read_old():
    """Pull existing rows out of an old-schema database (if any)."""
    if not os.path.exists(DB_PATH):
        return None
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    have = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    data = {}
    for t in TABLES:
        data[t] = [dict(r) for r in conn.execute(f"SELECT * FROM {t}")] if t in have else []
    conn.close()
    return data if any(data.values()) else None


def main():
    old = _read_old()
    if old:
        backup = DB_PATH + ".bak"
        shutil.copy(DB_PATH, backup)
        print(f"Backed up existing database to {backup}")
        os.remove(DB_PATH)

    conn = get_db()
    conn.executescript(SCHEMA)

    if old:
        for s in old["students"]:
            conn.execute(
                "INSERT OR IGNORE INTO students(id,username,password,name,roll_number,programme,"
                "department,academic_status,semester) VALUES (?,?,?,?,?,?,?,?,?)",
                (s["id"], s["username"], _hash(s["password"]), s["name"], s.get("roll_number"),
                 s.get("programme"), s.get("department"), s.get("academic_status") or "Active",
                 s.get("semester") or 1))
        for i in old["instructors"]:
            conn.execute("INSERT OR IGNORE INTO instructors VALUES (?,?,?,?,?)",
                         (i["id"], i["username"], _hash(i["password"]), i["name"], i.get("department")))
        for c in old["courses"]:
            conn.execute("INSERT OR IGNORE INTO courses(course_id,course_name,credits,instructor_id,capacity)"
                         " VALUES (?,?,?,?,?)",
                         (c["course_id"], c["course_name"], c["credits"],
                          c.get("instructor_id"), c.get("capacity") or 60))
        for r in old["registrations"]:
            conn.execute("INSERT OR IGNORE INTO registrations VALUES (?,?)",
                         (r["student_id"], r["course_id"]))
        for g in old["grades"]:
            conn.execute("INSERT OR IGNORE INTO grades(student_id,course_id,semester,grade) VALUES (?,?,?,?)",
                         (g["student_id"], g["course_id"], g["semester"], g["grade"]))

    # ---- sample data (only fills in what is missing) ----
    if conn.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 0:
        students = [
            (1, "arushia", "1234", "Arushia", "240001", "B.Tech", "Mechanical Engineering", "Active", 5),
            (2, "rahul", "1234", "Rahul", "240002", "B.Tech", "Computer Science and Engineering", "Active", 5),
        ]
        conn.executemany("INSERT INTO students VALUES (?,?,?,?,?,?,?,?,?)",
                         [(a, b, _hash(c), *rest) for a, b, c, *rest in students])

    instructors = [
        (1, "prof.rao", "teach123", "Prof. Rao", "Computer Science and Engineering"),
        (2, "prof.iyer", "teach123", "Prof. Iyer", "Mechanical Engineering"),
        (3, "prof.sen", "teach123", "Prof. Sen", "Sciences"),
    ]
    for i in instructors:
        conn.execute("INSERT OR IGNORE INTO instructors VALUES (?,?,?,?,?)",
                     (i[0], i[1], _hash(i[2]), i[3], i[4]))

    courses = [
        ("CS101", "Intro to Programming", 4, 1, 60),
        ("CS102", "Data Structures", 4, 1, 60),
        ("ME201", "Thermodynamics", 3, 2, 60),
        ("ME101", "Engineering Graphics", 3, 2, 60),
        ("EE250", "Signals and Systems", 4, 1, 60),
        ("MA101", "Mathematics I", 4, 3, 60),
        ("MA102", "Mathematics II", 4, 3, 60),
        ("PHY101", "Physics I", 4, 3, 60),
        ("CHM101", "Chemistry", 3, 3, 60),
    ]
    for c in courses:
        conn.execute("INSERT OR IGNORE INTO courses VALUES (?,?,?,?,?)", c)
    # assign instructors / capacity to pre-existing course rows that lack them
    for c in courses:
        conn.execute("UPDATE courses SET instructor_id=? WHERE course_id=? AND instructor_id IS NULL",
                     (c[3], c[0]))

    # demo grades for student 1 (semester 2 + a pass grade) so SPI/CPI have something to show
    if conn.execute("SELECT 1 FROM students WHERE id=1").fetchone():
        demo = [(1, "MA101", 1, "A"), (1, "PHY101", 1, "B"), (1, "CHM101", 1, "A"),
                (1, "MA102", 2, "B+"), (1, "ME101", 2, "A"), (1, "CS102", 2, "S")]
        for g in demo:
            conn.execute("INSERT OR IGNORE INTO grades(student_id,course_id,semester,grade) VALUES (?,?,?,?)", g)

    dupes = conn.execute("SELECT roll_number, GROUP_CONCAT(name, ', ') FROM students "
                         "GROUP BY roll_number HAVING COUNT(*) > 1").fetchall()
    for roll, names in dupes:
        print(f"WARNING: roll number {roll} is shared by: {names} -- please fix it in the database.")

    conn.commit()
    conn.close()
    print("Database ready.")


if __name__ == "__main__":
    main()
