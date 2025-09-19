import os
import tempfile
import json
from database import Database


def test_add_and_get_record():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        db = Database(path)
        db.connect()
        obj = {"pavilion": "P1", "name": "X"}
        rowid = db.add_record(obj)
        assert rowid is not None
        rec = db.get_record(rowid)
        assert rec is not None
        assert rec["pavilion"] == "P1"
        assert rec["data"]["name"] == "X"
        db.close()
    finally:
        os.remove(path)


def test_dedup():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        db = Database(path)
        db.connect()
        obj = {"pavilion": "P2", "name": "Dup"}
        rowid1 = db.add_record(obj)
        rowid2 = db.add_record({"name": "Dup", "pavilion": "P2"})  # same keys but different order
        assert rowid1 is not None
        assert rowid2 is None  # duplicate should be ignored
        all_records = list(db.all_records())
        assert len(all_records) == 1
        db.close()
    finally:
        os.remove(path)
