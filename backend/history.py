"""Inspect stored snapshots without generating or modifying readings."""

import argparse
import json
from pathlib import Path

from backend.storage import DEFAULT_DATABASE, SnapshotStore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--start", help="Inclusive ISO 8601 UTC timestamp")
    parser.add_argument("--end", help="Inclusive ISO 8601 UTC timestamp")
    args = parser.parse_args()
    if not args.database.is_file():
        parser.error("Database does not exist. Run python3 -m backend.simulator first.")
    try:
        rows = SnapshotStore(args.database).history(
            limit=args.limit, start=args.start, end=args.end)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
