import io
import json
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath

from database import DB_PATH

MEDIA_DIR = Path("uploaded_media")
BACKUP_FORMAT = "dasol-backup-v1"
REQUIRED_TABLES = (
    "place_archive",
    "place_archive_photos",
    "photo_gallery",
    "running_logs",
    "media_logs",
)
SAVED_PATH_TABLES = ("place_archive_photos", "photo_gallery", "media_logs")
ALLOWED_TOP_LEVEL = {"manifest.json", "dasol_hub.db", "uploaded_media"}


def _count_rows(conn, table):
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def _media_files():
    if not MEDIA_DIR.exists():
        return []
    return [path for path in MEDIA_DIR.rglob("*") if path.is_file()]


def build_backup_zip():
    """현재 서버의 DB와 사진을 zip 파일(bytes)로 만든다."""
    media_files = _media_files()
    with tempfile.TemporaryDirectory() as tmp:
        snapshot = Path(tmp) / "dasol_hub.db"

        # 앱이 사용 중이어도 일관된 상태로 DB를 복사한다.
        src = sqlite3.connect(DB_PATH)
        dst = sqlite3.connect(snapshot)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()

        conn = sqlite3.connect(snapshot)
        try:
            counts = {table: _count_rows(conn, table) for table in REQUIRED_TABLES}
        finally:
            conn.close()

        manifest = {
            "format": BACKUP_FORMAT,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "counts": counts,
            "media_files": len(media_files),
        }

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                "manifest.json",
                json.dumps(manifest, ensure_ascii=False, indent=2),
            )
            zf.write(snapshot, "dasol_hub.db")
            for path in media_files:
                arcname = PurePosixPath(
                    "uploaded_media", *path.relative_to(MEDIA_DIR).parts
                )
                zf.write(path, arcname.as_posix())
    return buffer.getvalue()


def _open_zip(data):
    try:
        return zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as error:
        raise ValueError("zip 파일을 열 수 없습니다. 백업 파일이 맞는지 확인해 주세요.") from error


def _validate_members(zf):
    names = zf.namelist()
    if "manifest.json" not in names or "dasol_hub.db" not in names:
        raise ValueError("백업 파일 구성이 올바르지 않습니다. (manifest.json 또는 dasol_hub.db 없음)")
    for name in names:
        path = PurePosixPath(name)
        if (
            not path.parts
            or path.is_absolute()
            or ".." in path.parts
            or "\\" in name
            or path.parts[0] not in ALLOWED_TOP_LEVEL
        ):
            raise ValueError(f"허용되지 않은 경로가 포함되어 있습니다: {name}")


def preview_backup(data):
    """복구하기 전에 백업 내용(시각, 개수)만 읽어 온다."""
    with _open_zip(data) as zf:
        _validate_members(zf)
        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
    if manifest.get("format") != BACKUP_FORMAT:
        raise ValueError("이 사이트에서 만든 백업 파일이 아닙니다.")
    return manifest


def _check_database(db_file):
    conn = sqlite3.connect(db_file)
    try:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        if integrity != "ok" or not set(REQUIRED_TABLES).issubset(tables):
            raise ValueError("백업 안의 DB 파일이 올바르지 않습니다.")
        for table in SAVED_PATH_TABLES:
            conn.execute(
                "UPDATE {} SET saved_path = REPLACE(saved_path, '\\', '/')".format(table)
            )
        conn.commit()
    finally:
        conn.close()


def restore_from_zip(data):
    """백업 zip으로 DB와 사진을 되돌린다."""
    manifest = preview_backup(data)
    tmp = Path(tempfile.mkdtemp(prefix=".restore_", dir="."))
    try:
        with _open_zip(data) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                target = tmp.joinpath(*PurePosixPath(info.filename).parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst)

        _check_database(tmp / "dasol_hub.db")

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        db_file = Path(DB_PATH)
        if db_file.exists():
            db_file.rename(
                db_file.with_name(f"{db_file.stem}_before_restore_{stamp}{db_file.suffix}")
            )
        shutil.move(str(tmp / "dasol_hub.db"), str(db_file))

        if MEDIA_DIR.exists():
            MEDIA_DIR.rename(f"uploaded_media_before_restore_{stamp}")
        new_media = tmp / "uploaded_media"
        if new_media.exists():
            shutil.move(str(new_media), str(MEDIA_DIR))
        else:
            MEDIA_DIR.mkdir(exist_ok=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return manifest