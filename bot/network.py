import logging
import socket
import subprocess
import re
from typing import List, Optional, Tuple

LOG = logging.getLogger(__name__)


def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def run_cmd(cmd: List[str]) -> str:
    try:
        LOG.debug("Running command: %s", cmd)
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, encoding="utf-8", errors="ignore")
        LOG.debug("Command output length: %d", len(output))
        return output
    except Exception as exc:  # broad exception because command failure isn't fatal
        LOG.exception("Command %s failed: %s", cmd, exc)
        return ""


def get_wifi_ssid() -> Optional[str]:
    out = run_cmd(["netsh", "wlan", "show", "interfaces"])
    if not out:
        LOG.debug("No output from netsh wlan show interfaces")
        return None
    m = re.search(r"^\s*SSID\s*:\s*(.+)$", out, re.MULTILINE)
    if m:
        ssid = m.group(1).strip()
        if ssid.lower() in ("<none>", "none"):
            return None
        return ssid
    return None


def parse_ipconfig_for_gateway_and_ip() -> Tuple[Optional[str], Optional[str]]:
    out = run_cmd(["ipconfig"]) or ""
    blocks = re.split(r"\r?\n\r?\n", out)
    for blk in blocks:
        if "Media State" in blk and "disconnected" in blk.lower():
            continue
        ip_match = re.search(r"IPv4 Address[\. ]*:\s*([0-9\.]+)", blk)
        gateway_match = re.search(r"Default Gateway[\. ]*:\s*([0-9\.]+)", blk)
        if ip_match:
            ip = ip_match.group(1)
            gw = gateway_match.group(1) if gateway_match else None
            LOG.debug("Found adapter ip=%s gw=%s", ip, gw)
            return ip, gw
    return get_local_ip(), None


def list_wifi_profiles() -> List[str]:
    out = run_cmd(["netsh", "wlan", "show", "profiles"]) or ""
    profiles = re.findall(r"All User Profile\s*:\s*(.+)", out)
    profs = [p.strip().strip('"') for p in profiles]
    LOG.debug("Found wifi profiles: %s", profs)
    return profs


def get_wifi_password(profile: str) -> Optional[str]:
    cmd = ["netsh", "wlan", "show", "profile", f"name={profile}", "key=clear"]
    out = run_cmd(cmd) or ""
    m = re.search(r"Key Content\s*:\s*(.+)", out)
    if m:
        pwd = m.group(1).strip()
        LOG.debug("Password for profile %s length=%d", profile, len(pwd))
        return pwd
    return None
