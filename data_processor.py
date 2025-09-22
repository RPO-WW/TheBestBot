import json
from typing import List, Dict, Any, Set, Generator, Union
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

    def load_from_json(self, file_path: str) -> List[Dict[str, Any]]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return self.load_from_dict(data)
        except Exception as e:
            print(f"Ошибка при загрузке JSON файла: {e}")
            return []

    def save_to_json(self, data: List[Dict[str, Any]], output_file: str) -> bool:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Данные сохранены в JSON: {output_file}")
            return True
        except Exception as e:
            print(f"Ошибка при сохранении JSON: {e}")
            return False

    def stream_json_objects(self, data: Union[Dict[str, Any], str]) -> Generator[Dict[str, Any], None, None]:
        try:
            if isinstance(data, str):
                with open(data, 'r', encoding='utf-8') as f:
                    data = json.load(f)

            if not isinstance(data, dict):
                raise ValueError("Данные должны быть словарем")

            def find_object_arrays(obj: Any) -> Union[List[Dict[str, Any]], None]:
                if isinstance(obj, list):
                    if obj and isinstance(obj[0], dict):
                        return obj
                    return None
                elif isinstance(obj, dict):
                    for value in obj.values():
                        result = find_object_arrays(value)
                        if result is not None:
                            return result
                return None

            array_data = find_object_arrays(data)
            if array_data is None:
                raise ValueError("В данных не найден массив объектов")

            for obj in array_data:
                if isinstance(obj, dict):
                    yield obj

        except Exception as e:
            print(f"Ошибка при потоковой обработке данных: {e}")
            raise

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
        signature_parts = []
        for field in self.unique_fields:
            value = obj.get(field)
            if value is None:
                signature_parts.append(f"{field}:None")
            elif isinstance(value, (list, dict)):
                signature_parts.append(f"{field}:{json.dumps(value, sort_keys=True)}")
            else:
                signature_parts.append(f"{field}:{value}")
        return "|".join(signature_parts)

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
                    if data[key] and isinstance(data[key][0], dict):
                        return data[key]

            for value in data.values():
                if isinstance(value, list):
                    if value and isinstance(value[0], dict):
                        return value

            def find_nested_object_arrays(obj: Any) -> Union[List[Dict[str, Any]], None]:
                if isinstance(obj, list):
                    if obj and isinstance(obj[0], dict):
                        return obj
                    return None
                elif isinstance(obj, dict):
                    for v in obj.values():
                        result = find_nested_object_arrays(v)
                        if result is not None:
                            return result
                return None

            nested_array = find_nested_object_arrays(data)
            if nested_array is not None:
                return nested_array

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
                print("Нет данных для обработки")
                return []

            unique_data = self.remove_duplicates(data)
            self.save_to_json(unique_data, output_file)

            print(f"Удалено {len(data) - len(unique_data)} дубликатов. "
                  f"Сохранено {len(unique_data)} уникальных записей.")

            return unique_data

        except Exception as e:
            print(f"Ошибка при обработке файлов: {e}")
            return []
