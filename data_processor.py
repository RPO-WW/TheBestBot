'''
Импортируем Stroka_Db
'''
from tools.stroka_db import Stroka_Db


class DataProcessor:
    '''Class DataProcessor'''

    def __init__(self, data):
        self.unique_fields = [
            "bssid",
            "freq",
            "rssi",
            "ssid",
            "timestamp",
            "volna",
            "tochka_dostupa",
            "password",
            "dns_server",
            "shluz",
            "local",
            "uroven_signala",
            "pavilion"
        ]
        self.data = data
        self.list_of_stroks = []

    def remove_duplicates(self, data_list=None):
        """Удаление дубликатов на основе уникальных полей"""

        if data_list is None:
            data_list = self.data
        if not data_list:
            return []

        seen = set()
        unique_data = []

        for item in data_list:
            key = tuple(item.get(field, "") for field in self.unique_fields)

            if key not in seen:
                seen.add(key)
                unique_data.append(item)

        return unique_data

    def logic(self):
        """Логика"""
        if not self.data:
            return []

        unique_data = self.remove_duplicates()
        self.list_of_stroks = []

        for self.data in unique_data:
            stroka = Stroka_Db()
            self.list_of_stroks.append(stroka)

        print(f"Создано {len(self.list_of_stroks)} объектов Stroka_Db")
        return self.list_of_stroks
