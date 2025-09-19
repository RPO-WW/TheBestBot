"""Simple database layer for TheBestBot.

This module provides a lightweight SQLite-backed `Database` class used by the
bot to persist incoming JSON-like objects. The implementation stores the raw
JSON (as text) plus a normalized SHA256 hash to support deduplication.

Assumptions made:
- Use SQLite via the stdlib `sqlite3` module.
- Each record is a JSON-serializable mapping (Python dict) and may contain a
  `pavilion` key which is commonly used by the bot flow. If `pavilion` is
  missing the value stored will be NULL and searching by pavilion will simply
  not return that record.

This file is intentionally small and dependency-free so it works in constrained
environments (e.g. simple hosting or CI).
"""

from __future__ import annotations

import json
import logging
import sqlite3
import hashlib
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

LOG = logging.getLogger(__name__)


def _normalize_and_hash(obj: Dict[str, Any]) -> str:
	"""Return a deterministic SHA256 hex digest for a JSON-serializable obj.

	We use `sort_keys=True` so semantically-equal dicts produce identical
	hashes (helps deduplication).
	"""
	dumped = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
	return hashlib.sha256(dumped.encode("utf-8")).hexdigest()


class Database:
	"""Simple SQLite-backed database helper.

	Usage:
	db = Database("./bot.db")
	db.connect()
	db.add_record({"pavilion": "A1", "name": "Stall 12"})
	"""

	def __init__(self, path: str = ":memory:") -> None:
		self.path = path
		self._conn: Optional[sqlite3.Connection] = None

	def connect(self) -> None:
		if self._conn:
			return
		LOG.debug("Connecting to sqlite db at %s", self.path)
		self._conn = sqlite3.connect(self.path, detect_types=sqlite3.PARSE_DECLTYPES)
		self._conn.row_factory = sqlite3.Row
		self._ensure_schema()

	def close(self) -> None:
		if self._conn:
			LOG.debug("Closing sqlite connection")
			self._conn.close()
			self._conn = None

	def _ensure_schema(self) -> None:
		assert self._conn is not None
		cur = self._conn.cursor()
		cur.execute(
			"""
			CREATE TABLE IF NOT EXISTS records (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				pavilion TEXT,
				data TEXT NOT NULL,
				data_hash TEXT NOT NULL UNIQUE,
				created_ts TEXT NOT NULL
			)
			"""
		)
		self._conn.commit()

	def add_record(self, obj: Dict[str, Any]) -> Optional[int]:
		"""Insert `obj` into the DB.

		Returns the new row id, or None if the record was a duplicate and was
		not inserted.
		"""
		if self._conn is None:
			self.connect()
		assert self._conn is not None

		data_hash = _normalize_and_hash(obj)
		data_text = json.dumps(obj, ensure_ascii=False)
		pavilion = obj.get("pavilion") if isinstance(obj, dict) else None
		created_ts = datetime.utcnow().isoformat() + "Z"

		cur = self._conn.cursor()
		try:
			cur.execute(
				"INSERT INTO records (pavilion, data, data_hash, created_ts) VALUES (?, ?, ?, ?)",
				(pavilion, data_text, data_hash, created_ts),
			)
			self._conn.commit()
			rowid = cur.lastrowid
			LOG.debug("Inserted record id=%s pavilion=%s", rowid, pavilion)
			return rowid
		except sqlite3.IntegrityError:
			# duplicate (data_hash unique)
			LOG.info("Duplicate record ignored (hash=%s)", data_hash)
			return None

	def get_record(self, rowid: int) -> Optional[Dict[str, Any]]:
		"""Return the record with `id==rowid` or None if not found."""
		if self._conn is None:
			self.connect()
		assert self._conn is not None
		cur = self._conn.cursor()
		cur.execute("SELECT * FROM records WHERE id = ?", (rowid,))
		row = cur.fetchone()
		if not row:
			return None
		return {"id": row["id"], "pavilion": row["pavilion"], "data": json.loads(row["data"]), "created_ts": row["created_ts"]}

	def find_by_pavilion(self, pavilion: str) -> List[Dict[str, Any]]:
		"""Return all records where `pavilion` equals the provided value."""
		if self._conn is None:
			self.connect()
		assert self._conn is not None
		cur = self._conn.cursor()
		cur.execute("SELECT * FROM records WHERE pavilion = ? ORDER BY id", (pavilion,))
		rows = cur.fetchall()
		return [
			{"id": r["id"], "pavilion": r["pavilion"], "data": json.loads(r["data"]), "created_ts": r["created_ts"]}
			for r in rows
		]

	def all_records(self) -> Iterable[Dict[str, Any]]:
		"""Yield all records in insertion order."""
		if self._conn is None:
			self.connect()
		assert self._conn is not None
		cur = self._conn.cursor()
		cur.execute("SELECT * FROM records ORDER BY id")
		for r in cur.fetchall():
			yield {"id": r["id"], "pavilion": r["pavilion"], "data": json.loads(r["data"]), "created_ts": r["created_ts"]}


if __name__ == "__main__":
	# simple smoke test when run directly
	logging.basicConfig(level=logging.DEBUG)
	db = Database()
	db.connect()
	a = {"pavilion": "A1", "name": "Booth 1", "items": ["x", "y"]}
	id1 = db.add_record(a)
	id2 = db.add_record(a)  # duplicate
	print("id1", id1, "id2", id2)
	print(list(db.all_records()))
	db.close()
