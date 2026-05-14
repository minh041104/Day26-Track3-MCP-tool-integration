from __future__ import annotations

import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "lab.db"


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    cohort TEXT NOT NULL,
    score REAL NOT NULL CHECK (score >= 0 AND score <= 100)
);

CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    credits INTEGER NOT NULL CHECK (credits > 0)
);

CREATE TABLE IF NOT EXISTS enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active', 'completed', 'dropped')),
    grade REAL CHECK (grade IS NULL OR (grade >= 0 AND grade <= 100)),
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
    UNIQUE (student_id, course_id)
);
"""


RESET_SQL = """
DELETE FROM enrollments;
DELETE FROM courses;
DELETE FROM students;
DELETE FROM sqlite_sequence WHERE name IN ('students', 'courses', 'enrollments');
"""


STUDENTS = [
    ("An Nguyen", "an.nguyen@example.edu", "A1", 88.5),
    ("Binh Tran", "binh.tran@example.edu", "A1", 91.0),
    ("Chi Le", "chi.le@example.edu", "B1", 79.5),
    ("Dung Pham", "dung.pham@example.edu", "B1", 84.0),
    ("Em Hoang", "em.hoang@example.edu", "A2", 95.0),
]


COURSES = [
    ("MCP101", "Model Context Protocol Foundations", 3),
    ("DB201", "Applied Databases", 4),
    ("AI310", "AI Tool Integration", 3),
]


ENROLLMENTS = [
    (1, 1, "completed", 90.0),
    (1, 2, "active", None),
    (2, 1, "completed", 93.0),
    (2, 3, "active", None),
    (3, 2, "completed", 78.0),
    (4, 2, "active", None),
    (5, 1, "completed", 96.0),
    (5, 3, "completed", 94.0),
]


def create_database(db_path: Path = DB_PATH) -> Path:
    """Create a reproducible SQLite database for the lab."""
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode = MEMORY")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(SCHEMA_SQL)
        conn.executescript(RESET_SQL)
        conn.executemany(
            "INSERT INTO students (name, email, cohort, score) VALUES (?, ?, ?, ?)",
            STUDENTS,
        )
        conn.executemany(
            "INSERT INTO courses (code, title, credits) VALUES (?, ?, ?)",
            COURSES,
        )
        conn.executemany(
            """
            INSERT INTO enrollments (student_id, course_id, status, grade)
            VALUES (?, ?, ?, ?)
            """,
            ENROLLMENTS,
        )
        conn.commit()

    return db_path


if __name__ == "__main__":
    created_path = create_database()
    print(f"Created database at {created_path}")
