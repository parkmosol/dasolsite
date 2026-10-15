import re
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
            distance_km REAL,
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
    running_columns = {
        row[1] for row in c.execute("PRAGMA table_info(running_logs)").fetchall()
    }
    if "distance_km" not in running_columns:
        c.execute("ALTER TABLE running_logs ADD COLUMN distance_km REAL")

    legacy_logs = c.execute(
        "SELECT id, course FROM running_logs WHERE distance_km IS NULL OR distance_km <= 0"
    ).fetchall()
    for log_id, course in legacy_logs:
        match = re.search(r"(\d+(?:\.\d+)?)\s*km", course, re.IGNORECASE)
        if match:
            distance_km = float(match.group(1))
            course_name = re.sub(
                r"\s*(?:\(|\[|-)?\s*\d+(?:\.\d+)?\s*km\s*[\)\]]?\s*$",
                "",
                course,
                flags=re.IGNORECASE,
            ).strip()
            c.execute(
                "UPDATE running_logs SET course = ?, distance_km = ? WHERE id = ?",
                (course_name or course, distance_km, log_id),
            )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS photo_gallery (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            saved_path TEXT NOT NULL,
            title TEXT NOT NULL,
            shot_date TEXT NOT NULL,
            location TEXT,
            description TEXT,
            iso TEXT,
            shutter_speed TEXT,
            aperture TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    c.execute(
        "CREATE INDEX IF NOT EXISTS idx_photo_gallery_shot_date ON photo_gallery(shot_date)"
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS place_archive (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT NOT NULL CHECK (status IN ('WANT', 'VISITED')),
            title TEXT NOT NULL,
            country TEXT NOT NULL,
            city TEXT,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            description TEXT,
            travel_goal TEXT,
            visit_date TEXT,
            memory TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS place_archive_photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            place_id INTEGER NOT NULL REFERENCES place_archive(id),
            filename TEXT NOT NULL,
            saved_path TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    c.execute(
        "CREATE INDEX IF NOT EXISTS idx_place_archive_status ON place_archive(status)"
    )
    c.execute(
        "CREATE INDEX IF NOT EXISTS idx_place_archive_photos_place ON place_archive_photos(place_id)"
    )
    conn.commit()
    conn.close()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn