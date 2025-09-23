import sqlite3
import re
from typing import Dict, List, Optional, Any


class WiFiDB:
    def __init__(self, db_path: str = "wifi_data.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS wifi_networks (
                    bssid TEXT PRIMARY KEY,
                    frequency INTEGER NOT NULL,
                    rssi INTEGER NOT NULL,
                    ssid TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    channel_bandwidth TEXT NOT NULL,
                    capabilities TEXT NOT NULL,
                    password TEXT,
                    dns_server TEXT,
                    gateway TEXT,
                    my_ip TEXT,
                    signal_level INTEGER,
                    pavilion_number INTEGER,
                    floor INTEGER
                )
            """)

            cursor.execute("PRAGMA table_info(wifi_networks)")
            columns = [col[1] for col in cursor.fetchall()]

            new_columns = {
                "password": "TEXT",
                "dns_server": "TEXT",
                "gateway": "TEXT",
                "my_ip": "TEXT",
                "signal_level": "INTEGER",
                "pavilion_number": "INTEGER",
                "floor": "INTEGER"
            }

            for col_name, col_type in new_columns.items():
                if col_name not in columns:
                    cursor.execute(f"ALTER TABLE wifi_networks ADD COLUMN {col_name} {col_type}")

            conn.commit()

    def checker(self, data: Dict[str, Any]) -> bool:
        try:
            required_keys = [
                "bssid", "frequency", "rssi",
                "ssid", "timestamp", "channel_bandwidth", "capabilities"
            ]
            for key in required_keys:
                if key not in data:
                    raise ValueError(f"Отсутствует обязательное поле: {key}")

            optional_string_fields = ["password", "dns_server", "gateway", "my_ip"]
            for field in optional_string_fields:
                if field in data and not isinstance(data[field], str):
                    raise ValueError(f"{field} должен быть строкой")

            for field in ["signal_level", "pavilion_number", "floor"]:  # <-- ДОБАВЛЕН floor
                if field in data:
                    if not isinstance(data[field], int):
                        raise ValueError(f"{field} должен быть целым числом")

            bssid_pattern = r'^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$'
            if not re.match(bssid_pattern, data["bssid"]):
                raise ValueError("Неверный формат BSSID (ожидается XX:XX:XX:XX:XX:XX)")

            if not isinstance(data["frequency"], int) or data["frequency"] <= 0:
                raise ValueError("frequency должен быть положительным целым числом")

            if not isinstance(data["rssi"], int) or not (-100 <= data["rssi"] <= 0):
                raise ValueError("rssi должен быть целым числом от -100 до 0")

            if not isinstance(data["timestamp"], int) or data["timestamp"] < 0:
                raise ValueError("timestamp должен быть неотрицательным целым числом")

            if not isinstance(data["ssid"], str) or len(data["ssid"]) == 0:
                raise ValueError("ssid должен быть непустой строкой")

            if not isinstance(data["channel_bandwidth"], str) or data["channel_bandwidth"] not in ["20", "40", "80", "160"]:
                raise ValueError("channel_bandwidth должен быть строкой: '20', '40', '80' или '160'")

            if not isinstance(data["capabilities"], str):
                raise ValueError("capabilities должен быть строкой")

            return True

        except Exception as e:
            print(f"[Ошибка валидации]: {e}")
            return False

    def create(self, data: Dict[str, Any]) -> bool:
        if not self.checker(data):
            return False

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO wifi_networks 
                    (bssid, frequency, rssi, ssid, timestamp, channel_bandwidth, capabilities, password, dns_server, gateway, my_ip, signal_level, pavilion_number, floor)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data["bssid"],
                    data["frequency"],
                    data["rssi"],
                    data["ssid"],
                    data["timestamp"],
                    data["channel_bandwidth"],
                    data["capabilities"],
                    data.get("password"),
                    data.get("dns_server"),
                    data.get("gateway"),
                    data.get("my_ip"),
                    data.get("signal_level"),
                    data.get("pavilion_number"),
                    data.get("floor")
                ))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            print("[Ошибка] Запись с таким BSSID уже существует.")
            return False
        except Exception as e:
            print(f"[Ошибка создания]: {e}")
            return False

    def read(self, bssid: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                if bssid:
                    cursor.execute("SELECT * FROM wifi_networks WHERE bssid = ?", (bssid,))
                else:
                    cursor.execute("SELECT * FROM wifi_networks")

                rows = cursor.fetchall()
                return [dict(row) for row in rows]

        except Exception as e:
            print(f"[Ошибка чтения]: {e}")
            return []

    def update(self, bssid: str, data: Dict[str, Any]) -> bool:
        if not self.checker(data):
            return False

        existing = self.read(bssid)
        if not existing:
            print(f"[Ошибка] Запись с BSSID {bssid} не найдена для обновления.")
            return False

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE wifi_networks SET
                        frequency = ?,
                        rssi = ?,
                        ssid = ?,
                        timestamp = ?,
                        channel_bandwidth = ?,
                        capabilities = ?,
                        password = ?,
                        dns_server = ?,
                        gateway = ?,
                        my_ip = ?,
                        signal_level = ?,
                        pavilion_number = ?,
                        floor = ?
                    WHERE bssid = ?
                """, (
                    data["frequency"],
                    data["rssi"],
                    data["ssid"],
                    data["timestamp"],
                    data["channel_bandwidth"],
                    data["capabilities"],
                    data.get("password"),
                    data.get("dns_server"),
                    data.get("gateway"),
                    data.get("my_ip"),
                    data.get("signal_level"),
                    data.get("pavilion_number"),
                    data.get("floor"),
                    bssid
                ))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"[Ошибка обновления]: {e}")
            return False

    def delete(self, bssid: str) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM wifi_networks WHERE bssid = ?", (bssid,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"[Ошибка удаления]: {e}")
            return False

    def crud_create(self, data):
        return self.create(data)

    def crud_read(self, bssid=None):
        return self.read(bssid)

    def crud_update(self, bssid, data):
        return self.update(bssid, data)

    def crud_delete(self, bssid):
        return self.delete(bssid)