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

        # Нормализация альтернативных имён полей
        if 'frequency' not in norm and 'frequency_mhz' in norm:
            norm['frequency'] = norm['frequency_mhz']
        if 'channel_bandwidth' not in norm and 'channel_bandwidth_mhz' in norm:
            try:
                bw = int(norm['channel_bandwidth_mhz'])
                norm['channel_bandwidth'] = str(bw)
            except (ValueError, TypeError):
                norm['channel_bandwidth'] = str(norm['channel_bandwidth_mhz'])

        # Нормализация timestamp (если в миллисекундах)
        if 'timestamp' in norm:
            ts = norm['timestamp']
            if isinstance(ts, (int, float)) and ts > 10**12:  # предполагаем миллисекунды
                norm['timestamp'] = int(ts // 1000)

        # Приведение типов (без валидации — это делает БД)
        try:
            frequency = int(norm.get('frequency', 0))
        except (ValueError, TypeError):
            frequency = 0

        try:
            rssi = int(norm.get('rssi', 0))
        except (ValueError, TypeError):
            rssi = 0

        try:
            timestamp = int(norm.get('timestamp', 0))
        except (ValueError, TypeError):
            timestamp = 0

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

    def update_network(self, bssid: str, password: Optional[str] = None, pavilion_number: Optional[int] = None) -> bool:
        existing = self.db.read(bssid)
        if not existing:
            logger.error(f"Запись с BSSID {bssid} не найдена для обновления.")
            return False

        # Берём существующие данные и обновляем только нужные поля
        record = existing[0]
        update_data = {
            'bssid': bssid,
            'frequency': record['frequency'],
            'rssi': record['rssi'],
            'ssid': record['ssid'],
            'timestamp': record['timestamp'],
            'channel_bandwidth': record['channel_bandwidth'],
            'capabilities': record['capabilities'],
            'password': password,
            'pavilion_number': pavilion_number,
            # Остальные поля оставляем как есть
            'dns_server': record.get('dns_server'),
            'gateway': record.get('gateway'),
            'my_ip': record.get('my_ip'),
            'signal_level': record.get('signal_level'),
            'floor': record.get('floor'),
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