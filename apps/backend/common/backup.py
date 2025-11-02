"""Database backup and recovery utilities.

Implements SQLite backup strategies with WAL mode configuration,
automated backup scheduling, and corruption recovery.
"""

import asyncio
import logging
import shutil
from datetime import datetime
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)


class DatabaseBackupManager:
    """Manages SQLite database backups and recovery."""

    def __init__(self, db_path: Path, backup_dir: Path):
        self.db_path = db_path
        self.backup_dir = backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    async def enable_wal_mode(self) -> bool:
        """Enable Write-Ahead Logging (WAL) mode for better concurrency.

        WAL mode allows multiple readers while a writer is active,
        and provides better crash recovery.
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Enable WAL mode
                await db.execute("PRAGMA journal_mode=WAL")

                # Configure checkpointing
                await db.execute("PRAGMA wal_autocheckpoint=1000")

                # Enable automatic vacuuming
                await db.execute("PRAGMA auto_vacuum=FULL")

                # Set synchronous mode to NORMAL (faster, still safe with WAL)
                await db.execute("PRAGMA synchronous=NORMAL")

                # Enable foreign keys
                await db.execute("PRAGMA foreign_keys=ON")

                await db.commit()

                # Verify settings
                cursor = await db.execute("PRAGMA journal_mode")
                mode = await cursor.fetchone()
                logger.info(f"Database journal mode: {mode[0] if mode else 'unknown'}")

                return True
        except Exception as e:
            logger.error(f"Failed to enable WAL mode: {e}")
            return False

    async def create_backup(self, backup_name: str | None = None) -> Path | None:
        """Create a backup of the database.

        Args:
            backup_name: Optional custom backup filename (without extension)

        Returns:
            Path to the backup file, or None if backup failed
        """
        if not self.db_path.exists():
            logger.warning(f"Database not found: {self.db_path}")
            return None

        try:
            # Generate backup filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if backup_name:
                backup_file = self.backup_dir / f"{backup_name}.db"
            else:
                backup_file = self.backup_dir / f"womcast_backup_{timestamp}.db"

            # Use SQLite's backup API for consistent snapshots
            async with aiosqlite.connect(self.db_path) as source:
                async with aiosqlite.connect(backup_file) as dest:
                    await source.backup(dest)

            # Also backup WAL and SHM files if they exist
            wal_file = Path(str(self.db_path) + "-wal")
            shm_file = Path(str(self.db_path) + "-shm")

            if wal_file.exists():
                shutil.copy2(wal_file, str(backup_file) + "-wal")
            if shm_file.exists():
                shutil.copy2(shm_file, str(backup_file) + "-shm")

            backup_size = backup_file.stat().st_size
            logger.info(
                f"Backup created: {backup_file.name} ({backup_size / 1024:.1f} KB)"
            )

            return backup_file
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return None

    async def restore_backup(self, backup_file: Path) -> bool:
        """Restore database from a backup file.

        Args:
            backup_file: Path to the backup file

        Returns:
            True if restore succeeded, False otherwise
        """
        if not backup_file.exists():
            logger.error(f"Backup file not found: {backup_file}")
            return False

        try:
            # Verify backup integrity
            if not await self.verify_database(backup_file):
                logger.error(f"Backup file is corrupted: {backup_file}")
                return False

            # Create a safety backup of current database
            if self.db_path.exists():
                safety_backup = self.db_path.parent / f"{self.db_path.name}.pre-restore"
                shutil.copy2(self.db_path, safety_backup)
                logger.info(f"Created safety backup: {safety_backup}")

            # Restore from backup
            shutil.copy2(backup_file, self.db_path)

            # Restore WAL and SHM files if they exist
            wal_backup = Path(str(backup_file) + "-wal")
            shm_backup = Path(str(backup_file) + "-shm")

            if wal_backup.exists():
                shutil.copy2(wal_backup, str(self.db_path) + "-wal")
            if shm_backup.exists():
                shutil.copy2(shm_backup, str(self.db_path) + "-shm")

            logger.info(f"Database restored from: {backup_file}")
            return True
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False

    async def verify_database(self, db_file: Path | None = None) -> bool:
        """Verify database integrity.

        Args:
            db_file: Optional path to database file (defaults to main database)

        Returns:
            True if database is healthy, False if corrupted
        """
        db_to_check = db_file or self.db_path

        if not db_to_check.exists():
            logger.error(f"Database file not found: {db_to_check}")
            return False

        try:
            async with aiosqlite.connect(db_to_check) as db:
                # Run integrity check
                cursor = await db.execute("PRAGMA integrity_check")
                result = await cursor.fetchone()

                if result and result[0] == "ok":
                    logger.info(f"Database integrity: OK ({db_to_check.name})")
                    return True
                else:
                    logger.error(
                        f"Database integrity: FAILED ({db_to_check.name}) - {result}"
                    )
                    return False
        except Exception as e:
            logger.error(f"Integrity check failed: {e}")
            return False

    async def cleanup_old_backups(self, keep_count: int = 7) -> int:
        """Remove old backup files, keeping only the most recent ones.

        Args:
            keep_count: Number of recent backups to keep

        Returns:
            Number of backups deleted
        """
        try:
            # Find all backup files
            backups = sorted(
                self.backup_dir.glob("womcast_backup_*.db"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )

            # Keep only the most recent
            deleted = 0
            for backup in backups[keep_count:]:
                backup.unlink()
                # Also remove WAL and SHM files
                wal_file = Path(str(backup) + "-wal")
                shm_file = Path(str(backup) + "-shm")
                if wal_file.exists():
                    wal_file.unlink()
                if shm_file.exists():
                    shm_file.unlink()
                deleted += 1
                logger.info(f"Deleted old backup: {backup.name}")

            return deleted
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return 0

    async def optimize_database(self) -> bool:
        """Optimize database by running VACUUM and ANALYZE.

        This reclaims unused space and updates query planner statistics.
        Should be run periodically (e.g., weekly).
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Checkpoint WAL before optimization
                await db.execute("PRAGMA wal_checkpoint(TRUNCATE)")

                # Run VACUUM to reclaim space
                logger.info("Running VACUUM...")
                await db.execute("VACUUM")

                # Run ANALYZE to update statistics
                logger.info("Running ANALYZE...")
                await db.execute("ANALYZE")

                await db.commit()
                logger.info("Database optimization complete")
                return True
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            return False

    def list_backups(self) -> list[tuple[Path, datetime, int]]:
        """List all available backups with metadata.

        Returns:
            List of tuples: (path, timestamp, size_bytes)
        """
        backups = []
        for backup_file in sorted(
            self.backup_dir.glob("womcast_backup_*.db"), reverse=True
        ):
            stat = backup_file.stat()
            timestamp = datetime.fromtimestamp(stat.st_mtime)
            backups.append((backup_file, timestamp, stat.st_size))
        return backups


async def main() -> None:
    """Test backup functionality."""
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    if len(sys.argv) < 2:
        print("Usage: python -m backup <command> [args]")
        print("Commands:")
        print("  enable-wal <db_path>")
        print("  backup <db_path> <backup_dir>")
        print("  restore <db_path> <backup_file>")
        print("  verify <db_path>")
        print("  cleanup <backup_dir> [keep_count]")
        print("  optimize <db_path>")
        sys.exit(1)

    command = sys.argv[1]

    if command == "enable-wal":
        db_path = Path(sys.argv[2])
        manager = DatabaseBackupManager(db_path, db_path.parent / "backups")
        success = await manager.enable_wal_mode()
        sys.exit(0 if success else 1)

    elif command == "backup":
        db_path = Path(sys.argv[2])
        backup_dir = Path(sys.argv[3])
        manager = DatabaseBackupManager(db_path, backup_dir)
        backup_file = await manager.create_backup()
        sys.exit(0 if backup_file else 1)

    elif command == "restore":
        db_path = Path(sys.argv[2])
        backup_file = Path(sys.argv[3])
        manager = DatabaseBackupManager(db_path, backup_file.parent)
        success = await manager.restore_backup(backup_file)
        sys.exit(0 if success else 1)

    elif command == "verify":
        db_path = Path(sys.argv[2])
        manager = DatabaseBackupManager(db_path, db_path.parent / "backups")
        success = await manager.verify_database()
        sys.exit(0 if success else 1)

    elif command == "cleanup":
        backup_dir = Path(sys.argv[2])
        keep_count = int(sys.argv[3]) if len(sys.argv) > 3 else 7
        db_path = backup_dir / "womcast.db"
        manager = DatabaseBackupManager(db_path, backup_dir)
        deleted = await manager.cleanup_old_backups(keep_count)
        print(f"Deleted {deleted} old backups")
        sys.exit(0)

    elif command == "optimize":
        db_path = Path(sys.argv[2])
        manager = DatabaseBackupManager(db_path, db_path.parent / "backups")
        success = await manager.optimize_database()
        sys.exit(0 if success else 1)

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
