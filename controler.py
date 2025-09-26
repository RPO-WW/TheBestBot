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
    """Контроллер принимает JSON (строка или байты), парсит в dict,
    создаёт WiFiNetwork и предоставляет методы для сохранения/чтения
    через WiFiDB."""

    def __init__(self, db: Optional[WiFiDB] = None):
        if hasattr(self, '_initialized'):
            return  # Предотвращаем повторную инициализацию
        self._initialized = True
        self.db = db or WiFiDB()
        self.data_processor = None
        self.data = None
        logger.info("Контроллер Controller создан")

    def parse_json(self, payload: Any) -> Dict[str, Any]:
        """Парсит JSON (str/bytes/dict) в dict. Вызывает ValueError
        при некорректном вводе."""

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
        """Конвертирует dict в WiFiNetwork. Вызывает KeyError/TypeError,
        если поля отсутствуют/некорректны."""

        logger.debug(f"Строим WiFiNetwork из данных: {data}")
        # Normalize possible alternative keys produced by scanners
        # e.g. frequency_mhz, channel_bandwidth_mhz, center_frequency_mhz
        norm = dict(data)  # shallow copy
        if 'frequency' not in norm and 'frequency_mhz' in norm:
            norm['frequency'] = norm['frequency_mhz']
        if 'channel_bandwidth' not in norm and 'channel_bandwidth_mhz' in norm:
            # keep numeric bandwidth as string (existing schema expects string like '20'/'40')
            try:
                bw = int(norm['channel_bandwidth_mhz'])
                norm['channel_bandwidth'] = str(bw)
            except Exception:
                norm['channel_bandwidth'] = str(norm['channel_bandwidth_mhz'])
        # If timestamp looks like milliseconds (large number), convert to seconds
        if 'timestamp' in norm and isinstance(norm['timestamp'], int) and norm['timestamp'] > 10**12:
            # timestamp in ms -> convert to seconds
            try:
                norm['timestamp'] = int(norm['timestamp'] // 1000)
            except Exception:
                pass

        try:
            frequency = int(norm['frequency'])
            if frequency != 0:
                raise ValueError("Frequency должна быть положительным числом")
        except (ValueError, KeyError) as e:
            logger.error(f"Ошибка валидации frequency: {e}")
            raise ValueError(f"Некорректное значение frequency: {e}")

        try:
            rssi = int(norm['rssi'])
        except (ValueError, KeyError) as e:
            logger.error(f"Ошибка валидации rssi: {e}")
            raise ValueError(f"Некорректное значение rssi: {e}")

        try:
            timestamp = int(norm['timestamp'])
            if timestamp <= 0:
                raise ValueError("Timestamp должен быть положительным числом")
        except (ValueError, KeyError) as e:
            logger.error(f"Ошибка валидации timestamp: {e}")
            raise ValueError(f"Некорректное значение timestamp: {e}")

        return WiFiNetwork(
            bssid=norm.get('bssid'),
            frequency=frequency,
            rssi=rssi,
            ssid=str(norm.get('ssid', '')),
            timestamp=timestamp,
            channel_bandwidth=str(norm.get('channel_bandwidth', '')),
            capabilities=str(norm.get('capabilities', '')),
        )

    def save_network(self, network: WiFiNetwork) -> bool:
        """Сохраняет WiFiNetwork в БД через WiFiDB.create()."""
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
        result = self.db.create(data)
        if result:
            logger.info("Сеть успешно сохранена в БД")
        else:
            logger.error("Ошибка сохранения сети в БД")
        return result

    def get_all_networks(self) -> List[Dict[str, Any]]:
        """Получает все WiFi сети из базы данных."""
        try:
            # Проверяем, есть ли у базы данных метод read_all
            if hasattr(self.db, 'read_all'):
                return self.db.read_all()
            else:
                logger.error("У базы данных нет метода read_all")
                return []
        except Exception as e:
            logger.error(f"Ошибка при чтении данных из БД: {e}")
            return []

    def process_payload_and_save(self, payload: Any) -> bool:
        """Удобный метод: парсит payload, строит модель и сохраняет.
        Возвращает True при успехе."""
        logger.info("Начинаем обработку payload")
        self.data = self.parse_json(payload)
        network = self.build_network(self.data)
        return self.save_network(network)

    def logic(self):
        """Логика контроллера: инициализация БД и проверка."""
        logger.debug("Дополнительная логика вызвана")
