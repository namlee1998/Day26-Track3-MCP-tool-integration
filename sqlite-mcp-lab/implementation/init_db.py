from __future__ import annotations

import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "sqlite_lab.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def drop_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP TABLE IF EXISTS enrollments;
        DROP TABLE IF EXISTS courses;
        DROP TABLE IF EXISTS students;
        """
    )


def create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            cohort TEXT NOT NULL,
            score REAL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            credits INTEGER NOT NULL
        );

        CREATE TABLE enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            grade REAL,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
        );
        """
    )


def seed_students(conn: sqlite3.Connection) -> None:
    students = [
        ("Nguyen An", "A1", 8.5, "2026-01-10T09:00:00"),
        ("Tran Binh", "A1", 7.8, "2026-01-11T09:00:00"),
        ("Le Chi", "A1", 9.1, "2026-01-12T09:00:00"),
        ("Pham Dung", "A2", 6.9, "2026-01-13T09:00:00"),
        ("Hoang Em", "A2", 8.0, "2026-01-14T09:00:00"),
        ("Do Giang", "A2", 7.2, "2026-01-15T09:00:00"),
        ("Bui Ha", "B1", 8.8, "2026-01-16T09:00:00"),
        ("Dang Khoa", "B1", 6.5, "2026-01-17T09:00:00"),
        ("Vu Linh", "B1", 9.4, "2026-01-18T09:00:00"),
        ("Phan Minh", "B2", 7.6, "2026-01-19T09:00:00"),
    ]

    conn.executemany(
        """
        INSERT INTO students (name, cohort, score, created_at)
        VALUES (?, ?, ?, ?);
        """,
        students,
    )


def seed_courses(conn: sqlite3.Connection) -> None:
    courses = [
        ("Introduction to AI", 3),
        ("Database Systems", 4),
        ("Python Programming", 3),
        ("Machine Learning", 4),
        ("Software Engineering", 3),
    ]

    conn.executemany(
        """
        INSERT INTO courses (title, credits)
        VALUES (?, ?);
        """,
        courses,
    )


def seed_enrollments(conn: sqlite3.Connection) -> None:
    enrollments = [
        (1, 1, 8.7),
        (1, 2, 8.2),
        (2, 1, 7.5),
        (2, 3, 8.0),
        (3, 4, 9.2),
        (3, 2, 8.9),
        (4, 3, 6.8),
        (5, 5, 8.1),
        (6, 2, 7.0),
        (7, 4, 8.9),
        (8, 1, 6.4),
        (9, 4, 9.6),
        (9, 5, 9.1),
        (10, 3, 7.7),
        (10, 5, 7.5),
    ]

    conn.executemany(
        """
        INSERT INTO enrollments (student_id, course_id, grade)
        VALUES (?, ?, ?);
        """,
        enrollments,
    )


def seed_data(conn: sqlite3.Connection) -> None:
    seed_students(conn)
    seed_courses(conn)
    seed_enrollments(conn)


def main() -> None:
    with get_connection() as conn:
        drop_tables(conn)
        create_tables(conn)
        seed_data(conn)
        conn.commit()

    print(f"Database initialized successfully: {DB_PATH}")


if __name__ == "__main__":
    main()