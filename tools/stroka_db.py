"""Данные о данных"""


class Stroka_Db:
    """Данные о данных"""
    def __init__(self):
        self.bssid: str = " "
        self.freq: int = 0
        self.rssi: int = 0
        self.ssid: str = " "
        self.timestamp: int = 0
        self.volna: str = " "
        self.tochka_dostupa: str = " "
        self.password: str = " "
        self.dns_server: str = " "
        self.shluz: str = " "
        self.local: str = " "
        self.uroven_signala: int = 0
        self.pavilion: int = 0

    def __str__(self):
        return f"Stroka_Db(bssid={self.bssid}, ssid={self.ssid}, rssi={self.rssi})"

    def __repr__(self):
        return self.__str__()
