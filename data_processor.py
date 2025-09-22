import json
from typing import List, Dict, Any, Set, Generator, Union, Optional
import pandas as pd
from pathlib import Path


class DataProcessor:
    def __init__(self, unique_fields: Optional[List[str]] = None):
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
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
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

            if not isinstance(data, (dict, list)):
                raise ValueError("Данные должны быть словарем или списком")

            def find_object_arrays(obj: Any) -> Optional[List[Dict[str, Any]]]:
                if isinstance(obj, list):
                    if obj and isinstance(obj[0], dict):
                        return obj
                    for item in obj:
                        result = find_object_arrays(item)
                        if result is not None:
                            return result
                    return None
                elif isinstance(obj, dict):
                    for value in obj.values():
                        result = find_object_arrays(value)
                        if result is not None:
                            return result
                    return None
                return None

            if isinstance(data, list) and data and isinstance(data[0], dict):
                array_data = data
            else:
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
                signature_parts.append("None")
            elif isinstance(value, (list, dict)):
                signature_parts.append(str(hash(json.dumps(value, sort_keys=True))))
            else:
                signature_parts.append(str(value))
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

            def find_nested_object_arrays(obj: Any) -> Optional[List[Dict[str, Any]]]:
                if isinstance(obj, list):
                    if obj and isinstance(obj[0], dict):
                        return obj
                    for item in obj:
                        result = find_nested_object_arrays(item)
                        if result is not None:
                            return result
                    return None
                elif isinstance(obj, dict):
                    for v in obj.values():
                        result = find_nested_object_arrays(v)
                        if result is not None:
                            return result
                    return None
                return None

            nested_array = find_nested_object_arrays(data)
            if nested_array is not None:
                return nested_array

            print("В словаре не найден массив объектов")
            return []

        except Exception as e:
            print(f"Ошибка при загрузке данных из словаря: {e}")
            return []

    def save_to_table(self, data: List[Dict[str, Any]], output_file: str) -> bool:
        try:
            if not data:
                print("Нет данных для сохранения")
                return False

            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            df = pd.DataFrame(data)
            df.to_csv(output_file, index=False, encoding='utf-8-sig')

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

    def process_folder(self, input_folder: str, output_file: str) -> List[Dict[str, Any]]:
        try:
            all_data = []
            input_path = Path(input_folder)
            
            if not input_path.exists() or not input_path.is_dir():
                print(f"Папка не найдена: {input_folder}")
                return []
            
            json_files = list(input_path.glob("*.json"))
            if not json_files:
                print(f"В папке {input_folder} не найдено JSON файлов")
                return []
            
            print(f"Найдено {len(json_files)} JSON файлов для обработки")
            
            for i, json_file in enumerate(json_files, 1):
                print(f"Обработка файла {i}/{len(json_files)}: {json_file.name}")
                
                try:
                    data = self.load_from_json(str(json_file))
                    if data:
                        all_data.extend(data)
                        print(f"  Загружено {len(data)} записей")
                    else:
                        print(f"  Файл пуст или содержит невалидные данные")
                except Exception as e:
                    print(f"  Ошибка при обработке файла {json_file.name}: {e}")
                    continue
            
            if not all_data:
                print("Не удалось загрузить данные из файлов")
                return []
            
            unique_data = self.remove_duplicates(all_data)
            
            if self.save_to_json(unique_data, output_file):
                print(f"\nОбработка завершена!")
                print(f"Всего загружено записей: {len(all_data)}")
                print(f"Уникальных записей: {len(unique_data)}")
                print(f"Удалено дубликатов: {len(all_data) - len(unique_data)}")
                print(f"Результат сохранен в: {output_file}")
            
            return unique_data
            
        except Exception as e:
            print(f"Ошибка при обработке папки: {e}")
            return []
    
    def process_folder_to_individual_files(self, input_folder: str, output_folder: str) -> Dict[str, List[Dict[str, Any]]]:
        try:
            input_path = Path(input_folder)
            output_path = Path(output_folder)
            output_path.mkdir(parents=True, exist_ok=True)
            
            if not input_path.exists() or not input_path.is_dir():
                print(f"Папка не найдена: {input_folder}")
                return {}
            
            json_files = list(input_path.glob("*.json"))
            if not json_files:
                print(f"В папке {input_folder} не найдено JSON файлов")
                return {}
            
            results = {}
            
            for i, json_file in enumerate(json_files, 1):
                print(f"Обработка файла {i}/{len(json_files)}: {json_file.name}")
                 
                try:
                    data = self.load_from_json(str(json_file))
                    if not data:
                        print(f"  Файл пуст или содержит невалидные данные")
                        continue
                    
                    unique_data = self.remove_duplicates(data)
                    
                    output_filename = f"processed_{json_file.stem}.json"
                    output_filepath = output_path / output_filename

                    if self.save_to_json(unique_data, str(output_filepath)):
                        results[str(json_file)] = unique_data
                        print(f"  Сохранено {len(unique_data)} уникальных записей в {output_filename}")
                    
                except Exception as e:
                    print(f"  Ошибка при обработке файла {json_file.name}: {e}")
                    continue
            
            return results
            
        except Exception as e:
            print(f"Ошибка при обработке папки: {e}")
            return {}
