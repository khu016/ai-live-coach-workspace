#!/usr/bin/env python3
"""Merge NIVI demo databases into one canonical database.

The oldest full database is copied as the base before this script is run.  Each
additional database is merged with fresh primary keys while all relationships
between trainings, transcript segments, bullets, recordings, and engagement
calls are remapped.  Recording files are copied into the canonical data folder.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
from pathlib import Path


def columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]


def rows(conn: sqlite3.Connection, table: str) -> list[sqlite3.Row]:
    return list(conn.execute(f"SELECT * FROM {table}"))


def next_id(conn: sqlite3.Connection, table: str) -> int:
    return conn.execute(f"SELECT COALESCE(MAX(id), 0) + 1 FROM {table}").fetchone()[0]


def insert_row(
    conn: sqlite3.Connection,
    table: str,
    row: sqlite3.Row,
    overrides: dict[str, object] | None = None,
    *,
    omit: set[str] | None = None,
    or_ignore: bool = False,
) -> None:
    overrides = overrides or {}
    omit = omit or set()
    available = set(row.keys()) | set(overrides)
    names = [name for name in columns(conn, table) if name in available and name not in omit]
    values = [overrides[name] if name in overrides else row[name] for name in names]
    verb = "INSERT OR IGNORE" if or_ignore else "INSERT"
    placeholders = ", ".join("?" for _ in names)
    conn.execute(
        f"{verb} INTO {table} ({', '.join(names)}) VALUES ({placeholders})",
        values,
    )


def remap_json_ids(value: object, mapping: dict[int, int]) -> object:
    if value in (None, ""):
        return value
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
    except (TypeError, json.JSONDecodeError):
        return value
    if not isinstance(parsed, list):
        return value
    return json.dumps([mapping.get(int(item), int(item)) for item in parsed])


def merge_source(dest: sqlite3.Connection, source_path: Path, recordings_dir: Path, tag: str) -> dict[str, int]:
    source = sqlite3.connect(source_path)
    source.row_factory = sqlite3.Row
    counts: dict[str, int] = {}
    try:
        training_map: dict[int, int] = {}
        start = next_id(dest, "trainings")
        for index, row in enumerate(rows(source, "trainings")):
            training_map[row["id"]] = start + index
        for row in rows(source, "trainings"):
            previous = row["prev_training_id"] if "prev_training_id" in row.keys() else None
            insert_row(
                dest,
                "trainings",
                row,
                {
                    "id": training_map[row["id"]],
                    "user_id": 1,
                    "prev_training_id": training_map.get(previous) if previous else None,
                },
            )
        counts["trainings"] = len(training_map)

        segment_map: dict[int, int] = {}
        start = next_id(dest, "transcript_segments")
        for index, row in enumerate(rows(source, "transcript_segments")):
            segment_map[row["id"]] = start + index
        for row in rows(source, "transcript_segments"):
            insert_row(
                dest,
                "transcript_segments",
                row,
                {"id": segment_map[row["id"]], "training_id": training_map[row["training_id"]]},
            )
        counts["transcript_segments"] = len(segment_map)

        bullet_map: dict[int, int] = {}
        start = next_id(dest, "bullet_events")
        for index, row in enumerate(rows(source, "bullet_events")):
            bullet_map[row["id"]] = start + index
        for row in rows(source, "bullet_events"):
            insert_row(
                dest,
                "bullet_events",
                row,
                {
                    "id": bullet_map[row["id"]],
                    "training_id": training_map[row["training_id"]],
                    "trigger_segment_id": segment_map.get(row["trigger_segment_id"]),
                    "response_segment_ids": remap_json_ids(row["response_segment_ids"], segment_map),
                },
            )
        counts["bullet_events"] = len(bullet_map)

        simple_tables = ("transcripts", "feedbacks")
        for table in simple_tables:
            start = next_id(dest, table)
            source_rows = rows(source, table)
            for index, row in enumerate(source_rows):
                insert_row(
                    dest,
                    table,
                    row,
                    {"id": start + index, "training_id": training_map[row["training_id"]]},
                )
            counts[table] = len(source_rows)

        recording_rows = rows(source, "recordings")
        start = next_id(dest, "recordings")
        recordings_dir.mkdir(parents=True, exist_ok=True)
        for index, row in enumerate(recording_rows):
            source_file = Path(row["file_path"])
            relocated_file = source_path.parent / "recordings" / source_file.name
            if relocated_file.is_file():
                source_file = relocated_file
            elif not source_file.is_absolute():
                source_file = source_path.parent / source_file
            suffix = source_file.suffix or ".webm"
            destination_file = recordings_dir / f"merged-{tag}-{row['id']}{suffix}"
            if source_file.is_file():
                shutil.copy2(source_file, destination_file)
            insert_row(
                dest,
                "recordings",
                row,
                {
                    "id": start + index,
                    "training_id": training_map[row["training_id"]],
                    "file_path": str(destination_file),
                    "size_bytes": destination_file.stat().st_size if destination_file.exists() else row["size_bytes"],
                },
            )
        counts["recordings"] = len(recording_rows)

        call_map: dict[int, int] = {}
        start = next_id(dest, "engagement_calls")
        for index, row in enumerate(rows(source, "engagement_calls")):
            call_map[row["id"]] = start + index
        for row in rows(source, "engagement_calls"):
            insert_row(
                dest,
                "engagement_calls",
                row,
                {
                    "id": call_map[row["id"]],
                    "training_id": training_map[row["training_id"]],
                    "trigger_segment_id": segment_map.get(row["trigger_segment_id"]),
                    "bullet_ids": remap_json_ids(row["bullet_ids"], bullet_map),
                    "merged_from_call_id": call_map.get(row["merged_from_call_id"]),
                },
            )
        counts["engagement_calls"] = len(call_map)

        for row in rows(source, "tutorial_progress"):
            existing = dest.execute(
                "SELECT id, completed FROM tutorial_progress WHERE user_id=1 AND tutorial_id=?",
                (row["tutorial_id"],),
            ).fetchone()
            if existing:
                if row["completed"] and not existing["completed"]:
                    dest.execute(
                        "UPDATE tutorial_progress SET completed=1, completed_at=?, updated_at=? WHERE id=?",
                        (row["completed_at"], row["updated_at"], existing["id"]),
                    )
            else:
                insert_row(dest, "tutorial_progress", row, {"user_id": 1}, omit={"id"})

        for row in rows(source, "analytics_events"):
            entity_id = row["entity_id"]
            if row["entity_type"] == "training" and entity_id:
                try:
                    entity_id = str(training_map.get(int(entity_id), int(entity_id)))
                except ValueError:
                    pass
            insert_row(
                dest,
                "analytics_events",
                row,
                {"user_id": 1 if row["user_id"] is not None else None, "entity_id": entity_id},
                omit={"id"},
            )

        for table in ("auth_sessions", "admin_sessions"):
            for row in rows(source, table):
                overrides = {"user_id": 1} if table == "auth_sessions" else {}
                insert_row(dest, table, row, overrides, omit={"id"}, or_ignore=True)
    finally:
        source.close()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    parser.add_argument("recordings_dir", type=Path)
    parser.add_argument("sources", nargs="+", type=Path)
    args = parser.parse_args()

    dest = sqlite3.connect(args.destination)
    dest.row_factory = sqlite3.Row
    try:
        # The base database may contain paths from its former checkout.  The
        # complete base data directory has already been copied beside this DB,
        # so make every existing recording self-contained in the canonical dir.
        for row in rows(dest, "recordings"):
            canonical_file = args.recordings_dir / Path(row["file_path"]).name
            if canonical_file.is_file():
                dest.execute(
                    "UPDATE recordings SET file_path=?, size_bytes=? WHERE id=?",
                    (str(canonical_file), canonical_file.stat().st_size, row["id"]),
                )
        for index, source in enumerate(args.sources, start=1):
            result = merge_source(dest, source, args.recordings_dir, f"source{index}")
            print(source, result)
        invite_hash = hashlib.sha256(b"nivi-test-one").hexdigest()
        dest.execute(
            "UPDATE users SET nickname=?, invite_code_hash=? WHERE id=1",
            ("小鹿主播", invite_hash),
        )
        dest.commit()
    except Exception:
        dest.rollback()
        raise
    finally:
        dest.close()


if __name__ == "__main__":
    main()
