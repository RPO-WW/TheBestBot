import json
from loguru import logger
from dataclasses import dataclass
from typing import Any, Dict, Optional

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
        try:
            frequency = int(data['frequency'])
            if frequency <= 0:
                raise ValueError("Frequency должна быть положительным числом")
        except (ValueError, KeyError) as e:
            logger.error(f"Ошибка валидации frequency: {e}")
            raise ValueError(f"Некорректное значение frequency: {e}")

        try:
            rssi = int(data['rssi'])
        except (ValueError, KeyError) as e:
            logger.error(f"Ошибка валидации rssi: {e}")
            raise ValueError(f"Некорректное значение rssi: {e}")

        try:
            timestamp = int(data['timestamp'])
            if timestamp <= 0:
                raise ValueError("Timestamp должен быть положительным числом")
        except (ValueError, KeyError) as e:
            logger.error(f"Ошибка валидации timestamp: {e}")
            raise ValueError(f"Некорректное значение timestamp: {e}")

        return WiFiNetwork(
            bssid=data['bssid'],
            frequency=frequency,
            rssi=rssi,
            ssid=str(data['ssid']),
            timestamp=timestamp,
            channel_bandwidth=str(data['channel_bandwidth']),
            capabilities=str(data['capabilities']),
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
        # Убрал тест, чтобы избежать повторных вызовов __init__
        # Если нужно, добавьте условную логику здесь
        pass
