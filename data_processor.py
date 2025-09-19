import json
from typing import List, Dict, Any, Set, Generator
from tabulate import tabulate


class DataProcessor:
    def __init__(self, unique_fields: List[str] = None):
        self.unique_fields = unique_fields

    def stream_json_objects(self, input_file: str) -> Generator[Dict[str, Any], None, None]:
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, list):
                raise ValueError("JSON должен быть списком объектов")
            for obj in data:
                yield obj  
        except Exception as e:
            print(f"Ошибка при потоковой обработке файла: {e}")

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

    def load_from_json(self, input_file: str) -> List[Dict[str, Any]]:
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, list):
                raise ValueError("JSON должен быть списком объектов")
            return data
        except Exception as e:
            print(f"Ошибка при загрузке файла: {e}")
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
