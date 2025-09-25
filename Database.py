import sqlite3
import re
from typing import Dict, List, Optional, Any, Union
from tools.stroka_db import Stroka_Db


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

    def _stroka_to_dict(self, stroka: Stroka_Db) -> Dict[str, Any]:
        return {
            "bssid": stroka.bssid,
            "frequency": stroka.freq,
            "rssi": stroka.rssi,
            "ssid": stroka.ssid,
            "timestamp": stroka.timestamp,
            "channel_bandwidth": stroka.volna,
            "capabilities": stroka.tochka_dostupa,
            "password": stroka.password if stroka.password != " " else None,
            "dns_server": stroka.dns_server if stroka.dns_server != " " else None,
            "gateway": stroka.shluz if stroka.shluz != " " else None,
            "my_ip": stroka.local if stroka.local != " " else None,
            "signal_level": stroka.uroven_signala if stroka.uroven_signala != 0 else None,
            "pavilion_number": stroka.pavilion if stroka.pavilion != 0 else None,
            "floor": stroka.floor if stroka.floor != 0 else None,
        }

    def checker(self, data: Dict[str, Any]) -> Union[bool, str]:
        # Проверка обязательных полей
        required_keys = [
            "bssid", "frequency", "rssi",
            "ssid", "timestamp", "channel_bandwidth", "capabilities"
        ]
        for key in required_keys:
            if key not in data:
                return f"Отсутствует обязательное поле: {key}"

        # Проверка типов необязательных строковых полей
        optional_string_fields = ["password", "dns_server", "gateway", "my_ip"]
        for field in optional_string_fields:
            if field in data and not isinstance(data[field], str):
                return f"Поле '{field}' должно быть строкой."

        # Проверка целочисленных необязательных полей
        optional_int_fields = ["signal_level", "pavilion_number", "floor"]
        for field in optional_int_fields:
            if field in data and not isinstance(data[field], int):
                return f"Поле '{field}' должно быть целым числом."

        # Валидация BSSID
        bssid_pattern = r'^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$'
        if not re.match(bssid_pattern, data["bssid"]):
            return "Неверный формат BSSID (ожидается XX:XX:XX:XX:XX:XX)"

        # Валидация frequency
        freq = data["frequency"]
        if not isinstance(freq, int) or freq <= 0:
            return "Поле 'frequency' должно быть положительным целым числом."

        # Валидация RSSI
        rssi = data["rssi"]
        if not isinstance(rssi, int) or not (-100 <= rssi <= 0):
            return "Поле 'rssi' должно быть целым числом в диапазоне от -100 до 0."

        # Валидация timestamp
        ts = data["timestamp"]
        if not isinstance(ts, int) or ts < 0:
            return "Поле 'timestamp' должно быть неотрицательным целым числом."

        # Валидация SSID
        ssid = data["ssid"]
        if not isinstance(ssid, str) or len(ssid) == 0:
            return "Поле 'ssid' должно быть непустой строкой."

        # Валидация ширины канала
        bw = data["channel_bandwidth"]
        if not isinstance(bw, str) or bw not in {"20", "40", "80", "160"}:
            return "Поле 'channel_bandwidth' должно быть одной из строк: '20', '40', '80', '160'."

        # Валидация capabilities
        cap = data["capabilities"]
        if not isinstance(cap, str):
            return "Поле 'capabilities' должно быть строкой."

        return True

    def create(self, data: Dict[str, Any]) -> bool:
        validation_result = self.checker(data)
        if validation_result is not True:
            print(f"[Ошибка валидации]: {validation_result}")
            return False

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO wifi_networks
                    (bssid, frequency, rssi, ssid, timestamp, channel_bandwidth, capabilities,
                     password, dns_server, gateway, my_ip, signal_level, pavilion_number, floor)
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
            print(f"[Ошибка создания записи]: {e}")
            return False

    def create_from_stroka(self, stroka: Stroka_Db) -> bool:
        data = self._stroka_to_dict(stroka)
        return self.create(data)

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

    def read_all(self) -> List[Dict[str, Any]]:
        return self.read()

    def update(self, bssid: str, data: Dict[str, Any]) -> bool:
        validation_result = self.checker(data)
        if validation_result is not True:
            print(f"[Ошибка валидации при обновлении]: {validation_result}")
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

    def update_from_stroka(self, bssid: str, stroka: Stroka_Db) -> bool:
        data = self._stroka_to_dict(stroka)
        if data["bssid"] != bssid:
            print("[Ошибка] BSSID в объекте не совпадает с целевым BSSID для обновления.")
            return False
        return self.update(bssid, data)

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

    # Совместимость с CRUD-интерфейсом
    def crud_create(self, data):
        if isinstance(data, Stroka_Db):
            return self.create_from_stroka(data)
        return self.create(data)

    def crud_read(self, bssid=None):
        return self.read(bssid)

    def crud_update(self, bssid, data):
        if isinstance(data, Stroka_Db):
            return self.update_from_stroka(bssid, data)
        return self.update(bssid, data)

    def crud_delete(self, bssid):
        return self.delete(bssid)