import os
import csv
from loguru import logger


def ensure_data_dir(base: str) -> str:
    try:
        path = os.path.join(base, "data")
        os.makedirs(path, exist_ok=True)
        logger.debug(f"Директория данных создана/проверена: {path}")
        return path
    except Exception as e:
        logger.error(f"Ошибка при создании директории данных: {e}")
        raise


def save_row(base: str, data: dict) -> None:
    try:
        dirp = ensure_data_dir(base)
        p = os.path.join(dirp, "table.csv")
        headers = ["name", "address", "password", "note"]

        # Подготовка данных для записи
        row = []
        for k in headers:
            value = data.get(k, "Отсутствует") or "Отсутствует"
            row.append(value)
            if value == "Отсутствует":
                logger.warning(f"Отсутствует значение для поля '{k}' в данных: {data}")

        exists = os.path.exists(p)

        with open(p, "a", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            if not exists:
                writer.writerow(headers)
                logger.info(f"Создан новый CSV файл с заголовками: {p}")
            writer.writerow(row)

        logger.info(f"Данные успешно сохранены в файл: {p}")
        logger.debug(f"Сохраненные данные: {data}")

    except PermissionError:
        logger.error(f"Ошибка доступа: нет прав на запись в файл {p}")
        raise
    except Exception as e:
        logger.exception(f"Неожиданная ошибка при сохранении данных: {e}")
        raise


def load_table(base: str) -> list:
    try:
        dirp = ensure_data_dir(base)
        p = os.path.join(dirp, "table.csv")

        if not os.path.exists(p):
            logger.warning(f"Файл данных не найден: {p}")
            return []

        rows = []
        with open(p, newline='', encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)

        logger.info(f"Загружено {len(rows)} записей из файла: {p}")
        logger.debug(f"Загруженные данные: {rows}")

        return rows

    except csv.Error as e:
        logger.error(f"Ошибка формата CSV в файле {p}: {e}")
        return []
    except PermissionError:
        logger.error(f"Ошибка доступа: нет прав на чтение файла {p}")
        return []
    except Exception as e:
        logger.exception(f"Неожиданная ошибка при загрузке данных: {e}")
        return []
