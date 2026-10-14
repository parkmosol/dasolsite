import sqlite3

DB_PATH = "dasol_hub.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS running_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            mood TEXT NOT NULL,
            course TEXT NOT NULL,
            time_sec INTEGER NOT NULL,
            pace TEXT NOT NULL,
            memo TEXT
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS media_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            filename TEXT NOT NULL,
            saved_path TEXT NOT NULL,
            uploaded_at TEXT NOT NULL
        )
        """
    )
    c.execute("SELECT COUNT(*) FROM courses")
    if c.fetchone()[0] == 0:
        defaults = [
            ("판암파출소 (6km)",),
            ("폐고속도로 (5km)",),
            ("한강 코스 (5km)",),
        ]
        c.executemany("INSERT INTO courses(name) VALUES (?)", defaults)
    conn.commit()
    conn.close()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn