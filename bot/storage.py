import os
import csv


def ensure_data_dir(base: str) -> str:
    path = os.path.join(base, "data")
    os.makedirs(path, exist_ok=True)
    return path


def save_row(base: str, data: dict) -> None:
    dirp = ensure_data_dir(base)
    p = os.path.join(dirp, "table.csv")
    headers = ["name", "address", "password", "note"]
    row = [data.get(k, "Отсутствует") or "Отсутствует" for k in headers]
    exists = os.path.exists(p)
    with open(p, "a", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        if not exists:
            writer.writerow(headers)
        writer.writerow(row)


def load_table(base: str) -> list:
    dirp = ensure_data_dir(base)
    p = os.path.join(dirp, "table.csv")
    if not os.path.exists(p):
        return []
    rows = []
    with open(p, newline='', encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows
