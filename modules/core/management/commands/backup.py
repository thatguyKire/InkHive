"""Back up the database and uploaded files, and delete backups past their retention.

    python manage.py backup              # make a backup, then prune old ones
    python manage.py backup --prune-only # only delete backups older than the limit
"""
import shutil
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

PREFIX = "backup-"
STAMP = "%Y%m%d-%H%M%S"


class Command(BaseCommand):
    help = "Copy the SQLite database and media into BACKUP_DIR, then delete backups older than BACKUP_RETENTION_DAYS."

    def add_arguments(self, parser):
        parser.add_argument("--prune-only", action="store_true", help="Only delete old backups.")

    def handle(self, *args, prune_only=False, **options):
        backup_dir = Path(settings.BACKUP_DIR)
        backup_dir.mkdir(parents=True, exist_ok=True)
        if not prune_only:
            self.create(backup_dir)
        self.prune(backup_dir)

    def create(self, backup_dir):
        if connection.vendor != "sqlite":
            raise CommandError("Only SQLite is supported here; use your database's own backup tool.")
        target = backup_dir / f"{PREFIX}{datetime.now(timezone.utc):{STAMP}}"
        target.mkdir(exist_ok=True)

        # SQLite's online backup, on its own connection, is safe while the app is running.
        src = sqlite3.connect(connection.settings_dict["NAME"], uri=True)
        dst = sqlite3.connect(target / "db.sqlite3")
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()

        media = Path(settings.MEDIA_ROOT)
        if media.is_dir():
            shutil.make_archive(str(target / "media"), "zip", media)
        self.stdout.write(f"Backed up to {target}")

    def prune(self, backup_dir):
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.BACKUP_RETENTION_DAYS)
        for path in sorted(backup_dir.glob(PREFIX + "*")):
            try:
                made = datetime.strptime(path.name[len(PREFIX):], STAMP).replace(tzinfo=timezone.utc)
            except ValueError:
                continue  # not one of ours
            if path.is_dir() and made < cutoff:
                shutil.rmtree(path)
                self.stdout.write(f"Deleted {path.name} (older than {settings.BACKUP_RETENTION_DAYS} days)")
