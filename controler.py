import json
from loguru import logger
from dataclasses import dataclass
from typing import Any, Dict, Optional
from io import BytesIO
from dotenv import load_dotenv
import os

from Database import WiFiDB

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

logger.add("file.log",
           format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
           rotation="3 days",
           backtrace=True,
           diagnose=True)

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
        self.db = db or WiFiDB()
        self.data_processor = None
        self.data = None

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
            raise ValueError(f"Некорректный JSON: {e}")

    def build_network(self, data: Dict[str, Any]) -> WiFiNetwork:
        """Конвертирует dict в WiFiNetwork. Вызывает KeyError/TypeError,
        если поля отсутствуют/некорректны."""

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
        return self.db.create(data)

    def process_payload_and_save(self, payload: Any) -> bool:
        """Удобный метод: парсит payload, строит модель и сохраняет.
        Возвращает True при успехе."""
        self.data = self.parse_json(payload)
        network = self.build_network(self.data)
        return self.save_network(network)

    def logic(self):
        """Плейсхолдер для дополнительной логики, например,
        обработки данных или взаимодействия с БД."""
        pass
