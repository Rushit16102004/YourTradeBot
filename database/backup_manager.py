"""
database/backup_manager.py
Automated Backup & Disaster Recovery Manager for NIFTY 50 Pro Terminal.
- Uses SQLite Online Backup API for non-blocking WAL-mode snapshotting.
- Packages users.db, all audit CSVs, and user drawings into compressed tar.gz archives.
- Maintains rolling retention (keeps last 14 backups).
- Can be invoked manually via Admin API or automatically on a daily schedule.
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import tarfile
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger("BackupManager")

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
DB_PATH = BASE_DIR / "users.db"
BACKUPS_DIR = PROJECT_ROOT / "backups"
BACKUPS_DIR.mkdir(parents=True, exist_ok=True)

MAX_BACKUPS_RETAINED = 14


def create_system_backup() -> Optional[Dict[str, Any]]:
    """
    Creates an atomic, non-blocking backup of the SQLite database and all user CSV logs.
    Returns metadata dict with backup path, size, and timestamp.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_dir = BACKUPS_DIR / f"temp_{timestamp}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    archive_path = BACKUPS_DIR / f"backup_{timestamp}.tar.gz"

    try:
        # 1. Atomic SQLite Online Backup (zero lock on active read/write queries)
        temp_db_path = temp_dir / "users.db"
        if DB_PATH.exists():
            with sqlite3.connect(DB_PATH) as src_conn:
                with sqlite3.connect(temp_db_path) as dst_conn:
                    src_conn.backup(dst_conn, pages=100)
            logger.info("SQLite online database backup completed: %s", temp_db_path)

        # 2. Copy active CSV data files if present
        csv_files = [
            "registered_users.csv",
            "user_login_records.csv",
            "copilot_chat_queries.csv",
            "visitor_daily_activity.csv"
        ]
        for fname in csv_files:
            src = PROJECT_ROOT / fname
            if src.exists():
                shutil.copy2(src, temp_dir / fname)

        # 3. Copy drawings cache if present
        drawings_cache = PROJECT_ROOT / "temp_storage" / "drawings.json"
        if drawings_cache.exists():
            shutil.copy2(drawings_cache, temp_dir / "drawings.json")

        # 4. Create compressed tar.gz archive
        with tarfile.open(archive_path, "w:gz") as tar:
            for item in temp_dir.iterdir():
                tar.add(item, arcname=item.name)

        archive_size_kb = round(archive_path.stat().st_size / 1024, 2)
        logger.info("Created system backup archive: %s (Size: %s KB)", archive_path.name, archive_size_kb)

        # 5. Cleanup temporary staging directory
        shutil.rmtree(temp_dir, ignore_errors=True)

        # 6. Apply rolling retention (delete oldest if > MAX_BACKUPS_RETAINED)
        clean_old_backups()

        return {
            "status": "ok",
            "filename": archive_path.name,
            "filepath": str(archive_path),
            "size_kb": archive_size_kb,
            "timestamp": timestamp,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")
        }

    except Exception as e:
        logger.error("Failed to create system backup: %s", e)
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None


def clean_old_backups():
    """Retains the most recent MAX_BACKUPS_RETAINED archives, deleting older ones."""
    try:
        archives = sorted(
            [f for f in BACKUPS_DIR.glob("backup_*.tar.gz")],
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        if len(archives) > MAX_BACKUPS_RETAINED:
            for old in archives[MAX_BACKUPS_RETAINED:]:
                try:
                    old.unlink()
                    logger.info("Purged old backup archive: %s", old.name)
                except Exception as ex:
                    logger.warning("Could not delete old backup %s: %s", old.name, ex)
    except Exception as e:
        logger.error("Error during backup cleanup: %s", e)


def list_available_backups() -> List[Dict[str, Any]]:
    """Returns a list of all existing backup archives with metadata."""
    archives = sorted(
        [f for f in BACKUPS_DIR.glob("backup_*.tar.gz")],
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    res = []
    for f in archives:
        stat = f.stat()
        res.append({
            "filename": f.name,
            "size_kb": round(stat.st_size / 1024, 2),
            "created_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        })
    return res


# Background automated daily backup thread
def start_daily_backup_scheduler():
    """Starts a non-blocking daemon thread creating a rolling backup every 24 hours."""
    def _runner():
        # Initial backup upon startup (after 60 seconds grace period)
        time_to_wait = 60
        import time
        time.sleep(time_to_wait)
        create_system_backup()

        # Subsequent backups every 24 hours (86,400 seconds)
        while True:
            time.sleep(86400)
            create_system_backup()

    t = threading.Thread(target=_runner, daemon=True, name="DailyBackupScheduler")
    t.start()
    logger.info("Daily automated backup scheduler thread started.")
