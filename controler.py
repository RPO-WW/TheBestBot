import json
from loguru import logger
from dataclasses import dataclass
from typing import Any, Dict, Optional, List

from Database import WiFiDB

logger.info("Контроллер инициализирован")


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
    def __init__(self, db: Optional[WiFiDB] = None):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self.db = db or WiFiDB()
        logger.info("Контроллер Controller создан")

    def parse_json(self, payload: Any) -> Dict[str, Any]:
        if isinstance(payload, dict):
            return payload
        try:
            if isinstance(payload, bytes):
                payload = payload.decode('utf-8')
            return json.loads(payload)
        except Exception as e:
            logger.error(f"Ошибка парсинга JSON: {e}")
            raise ValueError(f"Некорректный JSON: {e}")

    def build_network(self, data: Dict[str, Any]) -> WiFiNetwork:
        norm = dict(data)
        if 'frequency' not in norm and 'frequency_mhz' in norm:
            norm['frequency'] = norm['frequency_mhz']
        if 'channel_bandwidth' not in norm and 'channel_bandwidth_mhz' in norm:
            try:
                bw = int(norm['channel_bandwidth_mhz'])
                norm['channel_bandwidth'] = str(bw)
            except Exception:
                norm['channel_bandwidth'] = str(norm['channel_bandwidth_mhz'])
        if 'timestamp' in norm and isinstance(norm['timestamp'], int) and norm['timestamp'] > 10**12:
            try:
                norm['timestamp'] = int(norm['timestamp'] // 1000)
            except Exception:
                pass

        # Валидация frequency
        try:
            frequency = int(norm['frequency'])
            if frequency <= 0:
                raise ValueError("Frequency должна быть положительным числом")
        except (ValueError, KeyError) as e:
            logger.error(f"Ошибка валидации frequency: {e}")
            raise ValueError(f"Некорректное значение frequency: {e}")

        # Валидация rssi
        try:
            rssi = int(norm['rssi'])
            if rssi > 0 or rssi < -100:
                raise ValueError("RSSI должен быть в диапазоне от -100 до 0")
        except (ValueError, KeyError) as e:
            logger.error(f"Ошибка валидации rssi: {e}")
            raise ValueError(f"Некорректное значение rssi: {e}")

        # Валидация timestamp
        try:
            timestamp = int(norm['timestamp'])
            if timestamp <= 0:
                raise ValueError("Timestamp должен быть положительным числом")
        except (ValueError, KeyError) as e:
            logger.error(f"Ошибка валидации timestamp: {e}")
            raise ValueError(f"Некорректное значение timestamp: {e}")

        return WiFiNetwork(
            bssid=str(norm.get('bssid', "")),
            frequency=frequency,
            rssi=rssi,
            ssid=str(norm.get('ssid', '')),
            timestamp=timestamp,
            channel_bandwidth=str(norm.get('channel_bandwidth', '')),
            capabilities=str(norm.get('capabilities', '')),
        )

    def save_network(self, network: WiFiNetwork) -> Optional[str]:
        data = {
            'bssid': network.bssid,
            'frequency': network.frequency,
            'rssi': network.rssi,
            'ssid': network.ssid,
            'timestamp': network.timestamp,
            'channel_bandwidth': network.channel_bandwidth,
            'capabilities': network.capabilities,
        }
        logger.info(f"Сохраняем сеть: {network.ssid} ({network.bssid})")
        success = self.db.create(data)
        if success:
            logger.info("Сеть успешно сохранена в БД")
            return network.bssid
        else:
            logger.error("Ошибка сохранения сети в БД")
            return None

    def update_network(self, bssid: str, password: str = "", pavilion_number: int = 0) -> bool:
        existing = self.db.read(bssid)
        if not existing:
            logger.error(f"Запись с BSSID {bssid} не найдена для обновления.")
            return False

        update_data = {
            'bssid': bssid,
            'frequency': existing[0]['frequency'],
            'rssi': existing[0]['rssi'],
            'ssid': existing[0]['ssid'],
            'timestamp': existing[0]['timestamp'],
            'channel_bandwidth': existing[0]['channel_bandwidth'],
            'capabilities': existing[0]['capabilities'],
            'password': password,
            'pavilion_number': pavilion_number,
        }

        success = self.db.update(bssid, update_data)
        if success:
            logger.info(f"Запись {bssid} успешно обновлена с паролем и павильоном")
        else:
            logger.error(f"Не удалось обновить запись {bssid}")
        return success

    def get_all_networks(self) -> List[Dict[str, Any]]:
        try:
            return self.db.read_all()
        except Exception as e:
            logger.error(f"Ошибка при чтении данных из БД: {e}")
            return []

    def process_payload_and_save(self, payload: Any) -> bool:
        logger.info("Начинаем обработку payload")
        self.data = self.parse_json(payload)
        network = self.build_network(self.data)
        return self.save_network(network) is not None

    def logic(self):
        logger.debug("Дополнительная логика вызвана")