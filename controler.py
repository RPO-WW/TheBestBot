import json
from dataclasses import dataclass
from typing import Any, Dict, Optional

from Database import WiFiDB


@dataclass
class WiFiNetwork:
    bssid: str
    frequency: int
    rssi: int
    ssid: str
    timestamp: int
    channel_bandwidth: str
    capabilities: str


class Controller:
    """Controller accepts JSON (string or bytes), parses into dict,
    creates a WiFiNetwork instance and provides
      methods to save/read via WiFiDB.
    """

    def __init__(self, db: Optional[WiFiDB] = None):
        self.db = db or WiFiDB()

        self.data_processor = None
        self.data = None

    def parse_json(self, payload: Any) -> Dict[str, Any]:
        """Parse input JSON (str/bytes/dict) to a dict. Raises
          ValueError on bad input."""

        if isinstance(payload, dict):
            return payload
        try:
            if isinstance(payload, bytes):
                payload = payload.decode('utf-8')
            return json.loads(payload)
        except Exception as e:
            raise ValueError(f"Invalid JSON payload: {e}")

    def build_network(self, data: Dict[str, Any]) -> WiFiNetwork:
        """Convert dict to WiFiNetwork dataclass. Will raise
          KeyError/TypeError if fields missing/invalid."""

        return WiFiNetwork(
            bssid=data['bssid'],
            frequency=int(data['frequency']),
            rssi=int(data['rssi']),
            ssid=str(data['ssid']),
            timestamp=int(data['timestamp']),
            channel_bandwidth=str(data['channel_bandwidth']),
            capabilities=str(data['capabilities']),
        )

    def save_network(self, network: WiFiNetwork) -> bool:
        """Save WiFiNetwork to DB via WiFiDB.create()"""
        data = {
            'bssid': network.bssid,
            'frequency': network.frequency,
            'rssi': network.rssi,
            'ssid': network.ssid,
            'timestamp': network.timestamp,
            'channel_bandwidth': network.channel_bandwidth,
            'capabilities': network.capabilities,
        }
        return self.db.create(data)

    def process_payload_and_save(self, payload: Any) -> bool:

        """Convenience method: parse payload, build model, and save.
          Returns True on success."""
        self.data = self.parse_json(payload)
        network = self.build_network(self.data)
        return self.save_network(network)

    def logic(self):
        """Placeholder for additional logic, e.g., processing data
          or interacting with DB."""
        pass
