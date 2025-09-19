import socket
import subprocess
import re
from typing import List, Optional, Tuple
from loguru import logger


def get_local_ip() -> str:
    logger.debug("Получение локального IP адреса")
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        logger.info(f"Локальный IP адрес определен: {ip}")
        return ip
    except Exception as e:
        logger.warning(f"Не удалось определить локальный IP, используется 127.0.0.1: {e}")
        return "127.0.0.1"
    finally:
        s.close()


def run_cmd(cmd: List[str]) -> str:
    logger.debug(f"Выполнение команды: {' '.join(cmd)}")
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, encoding="utf-8", errors="ignore")
        logger.debug(f"Команда выполнена успешно, вывод: {output[:100]}...")  # Логируем первые 100 символов
        return output
    except subprocess.CalledProcessError as e:
        logger.error(f"Команда завершилась с ошибкой (код {e.returncode}): {' '.join(cmd)}")
        return ""
    except FileNotFoundError:
        logger.error(f"Команда не найдена: {' '.join(cmd)}")
        return ""
    except Exception as e:
        logger.exception(f"Неожиданная ошибка при выполнении команды: {e}")
        return ""


def get_wifi_ssid() -> Optional[str]:
    logger.debug("Получение SSID WiFi сети")
    out = run_cmd(["netsh", "wlan", "show", "interfaces"])
    if not out:
        logger.warning("Не удалось получить информацию о WiFi интерфейсах")
        return None
    
    m = re.search(r"^\s*SSID\s*:\s*(.+)$", out, re.MULTILINE)
    if m:
        ssid = m.group(1).strip()
        if ssid.lower() in ("<none>", "none"):
            logger.info("WiFi подключение отсутствует (SSID: <none>)")
            return None
        logger.info(f"Найден SSID WiFi сети: {ssid}")
        return ssid
    
    logger.debug("SSID не найден в выводе команды")
    return None


def parse_ipconfig_for_gateway_and_ip() -> Tuple[Optional[str], Optional[str]]:
    logger.debug("Анализ вывода ipconfig для поиска шлюза и IP")
    out = run_cmd(["ipconfig"]) or ""
    
    if not out:
        logger.warning("Команда ipconfig не вернула данных, используем get_local_ip()")
        ip = get_local_ip()
        return ip, None
    
    blocks = re.split(r"\r?\n\r?\n", out)
    logger.debug(f"Найдено {len(blocks)} блоков в выводе ipconfig")
    
    for i, blk in enumerate(blocks):
        if "Media State" in blk and "disconnected" in blk.lower():
            logger.debug(f"Блок {i}: интерфейс отключен, пропускаем")
            continue
        
        ip_match = re.search(r"IPv4 Address[\. ]*:\s*([0-9\.]+)", blk)
        gateway_match = re.search(r"Default Gateway[\. ]*:\s*([0-9\.]+)", blk)
        
        if ip_match:
            ip = ip_match.group(1)
            gw = gateway_match.group(1) if gateway_match else None
            
            if gw:
                logger.info(f"Найден IP: {ip}, шлюз: {gw}")
            else:
                logger.info(f"Найден IP: {ip}, шлюз не найден")
            
            return ip, gw
    
    logger.warning("IP и шлюз не найдены в ipconfig, используем get_local_ip()")
    ip = get_local_ip()
    return ip, None


def list_wifi_profiles() -> List[str]:
    logger.debug("Получение списка WiFi профилей")
    out = run_cmd(["netsh", "wlan", "show", "profiles"]) or ""
    
    if not out:
        logger.warning("Не удалось получить список WiFi профилей")
        return []
    
    profiles = re.findall(r"All User Profile\s*:\s*(.+)", out)
    cleaned_profiles = [p.strip().strip('"') for p in profiles]
    
    logger.info(f"Найдено {len(cleaned_profiles)} WiFi профилей: {cleaned_profiles}")
    return cleaned_profiles


def get_wifi_password(profile: str) -> Optional[str]:
    logger.debug(f"Получение пароля для WiFi профиля: {profile}")
    cmd = ["netsh", "wlan", "show", "profile", f"name={profile}", "key=clear"]
    out = run_cmd(cmd) or ""
    
    if not out:
        logger.warning(f"Не удалось получить информацию о профиле: {profile}")
        return None
    
    m = re.search(r"Key Content\s*:\s*(.+)", out)
    if m:
        password = m.group(1).strip()
        if password:
            logger.info(f"Пароль для профиля '{profile}' успешно получен")
            return password
        else:
            logger.warning(f"Пароль для профиля '{profile}' пустой")
            return None
    
    # Дополнительная проверка на открытые сети
    if "Authentication\s*:\s*Open" in out:
        logger.info(f"Профиль '{profile}' использует открытую сеть (без пароля)")
        return None
    
    logger.warning(f"Пароль не найден для профиля: {profile}")
    return None
