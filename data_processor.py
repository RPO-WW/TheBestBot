import json
from typing import List, Dict, Any, Set, Generator
import pandas as pd


class DataProcessor:
    def __init__(self, unique_fields: List[str] = None):
        if unique_fields is None:
            unique_fields = [
                "bssid",
                "frequency_mhz",
                "rssi",
                "ssid",
                "timestamp",
                "channel_bandwidth_mhz",
                "capabilities"
            ]
        self.unique_fields = unique_fields

    def stream_json_objects(self, data: Dict[str, Any]) -> Generator[Dict[str, Any], None, None]:
        try:
            if not isinstance(data, dict):
                raise ValueError("Данные должны быть словарем")

            def find_arrays(obj):
                if isinstance(obj, list):
                    return obj
                elif isinstance(obj, dict):
                    for value in obj.values():
                        result = find_arrays(value)
                        if result is not None:
                            return result
                return None
            array_data = find_arrays(data)
            if array_data is None:
                raise ValueError("В данных не найден массив объектов")
            for obj in array_data:
                yield obj 
        except Exception as e:
            print(f"Ошибка при потоковой обработке данных: {e}")

    def process_streamed_data(self, input_file: str, output_file: str) -> List[Dict[str, Any]]:
        seen_signatures: Set[str] = set()
        unique_data: List[Dict[str, Any]] = []
        try:
            for obj in self.stream_json_objects(input_file):
                signature = self._get_object_signature(obj)
                if signature not in seen_signatures:
                    seen_signatures.add(signature)
                    unique_data.append(obj)
            self.save_to_json(unique_data, output_file)
            print(f"Обработано в потоковом режиме. Уникальных записей: {len(unique_data)}")
            return unique_data
        except Exception as e:
            print(f"Ошибка при потоковой обработке: {e}")
            return []

    def _get_object_signature(self, obj: Dict[str, Any]) -> str:
        if self.unique_fields:
            signature_parts = []
            for field in self.unique_fields:
                if field in obj:
                    signature_parts.append(f"{field}:{obj[field]}")
                else:
                    signature_parts.append(f"{field}:None")
            return "|".join(signature_parts)
        else:
            return json.dumps(obj, sort_keys=True)

    def remove_duplicates(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen_signatures: Set[str] = set()
        unique_data: List[Dict[str, Any]] = []
        for item in data:
            signature = self._get_object_signature(item)
            if signature not in seen_signatures:
                seen_signatures.add(signature)
                unique_data.append(item)
        return unique_data

    def load_from_dict(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        try:
            common_keys = ['results', 'data', 'items', 'objects', 'entries']
            for key in common_keys:
                if key in data and isinstance(data[key], list):
                    return data[key]
            for value in data.values():
                if isinstance(value, list):
                    return value
            raise ValueError("В словаре не найден массив объектов")
        except Exception as e:
            print(f"Ошибка при загрузке данных из словаря: {e}")
            return []

    def save_to_table(self, data: List[Dict[str, Any]], output_file: str) -> bool:
        try:
            if not data:
                print("Нет данных для сохранения")
                return False
            df = pd.DataFrame(data)
            df.to_csv(output_file, index=False, encoding='utf-8')
            print(f"Данные сохранены в таблицу: {output_file}")
            print(f"Количество записей: {len(df)}")
            print(f"Количество столбцов: {len(df.columns)}")
            print(f"Столбцы: {list(df.columns)}")
            return True
        except Exception as e:
            print(f"Ошибка при сохранении таблицы: {e}")
            return False

    def process_file(self, input_file: str, output_file: str) -> List[Dict[str, Any]]:
        try:
            data = self.load_from_json(input_file)
            if not data:
                return []
            unique_data = self.remove_duplicates(data)
            self.save_to_json(unique_data, output_file)
            print(f"Удалено {len(data) - len(unique_data)} дубликатов. "
                  f"Сохранено {len(unique_data)} уникальных записей.")
            return unique_data
        except Exception as e:
            print(f"Ошибка при обработке файлов: {e}")
            return []
