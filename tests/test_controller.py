import json
import pytest
from pathlib import Path

from controler import Controller
from database import WiFiDB


def test_process_payload_and_save_success(tmp_path: Path):
    db_path = str(tmp_path / "test_wifi.db")
    db = WiFiDB(db_path=db_path)
    controller = Controller(db=db)

    payload = {
        "bssid": "aa:bb:cc:dd:ee:ff",
        "frequency": 2412,
        "rssi": -50,
        "ssid": "TestNet",
        "timestamp": 1234567890,
        "channel_bandwidth": "20",
        "capabilities": "[WPA2]",
    }

    json_payload = json.dumps(payload)
    assert controller.process_payload_and_save(json_payload) is True

    rows = controller.db.read(payload['bssid'])
    assert len(rows) == 1
    assert rows[0]['bssid'] == payload['bssid']
    assert int(rows[0]['rssi']) == payload['rssi']


def test_process_payload_and_save_invalid_json():
    db = WiFiDB(db_path=":memory:")
    controller = Controller(db=db)
    with pytest.raises(ValueError):
        controller.process_payload_and_save("not a json")
