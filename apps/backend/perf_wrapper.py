"""Performance test wrapper for indexer.

Wraps the indexer to avoid relative import issues when running from perf script.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.database import init_database  # noqa: E402
from metadata.indexer import (  # noqa: E402
    detect_deleted_files,
    initialize_mount_point,
    scan_mount_point,
)


async def main():
    if len(sys.argv) < 2:
        print("Usage: python perf_wrapper.py <mount_path>")
        sys.exit(1)

    mount_path = Path(sys.argv[1])
    if not mount_path.exists():
        print(f"Error: {mount_path} does not exist")
        sys.exit(1)

    db_path = Path("womcast.db")
    await init_database(db_path)

    mount_id = await initialize_mount_point(db_path, str(mount_path), mount_path.name)

    scanned, indexed = await scan_mount_point(db_path, mount_path, mount_id)
    print(f"Indexed {indexed}/{scanned} files")

    deleted = await detect_deleted_files(db_path, mount_id)
    print(f"Removed {deleted} deleted files")


if __name__ == "__main__":
    asyncio.run(main())
