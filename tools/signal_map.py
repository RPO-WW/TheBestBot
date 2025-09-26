#!/usr/bin/env python3
"""Renderer and formatter to produce table like the user's screenshot.

This module provides `format_records(records)` which returns a formatted
string with columns: BSSID | SSID | RSSI | FREQ | TIMESTAMP. It's intentionally
plain-text so it can be piped to logs or saved to files.

Example record fields expected: 'bssid', 'ssid', 'rssi', 'freq', 'timestamp'
"""

from __future__ import annotations
from typing import Iterable, Mapping
import time


def format_records(records: Iterable[Mapping]) -> str:
    """Format records into a table with header matching screenshot.

    Each record should provide keys: bssid, ssid, rssi, freq, timestamp.
    Missing keys are replaced with sensible defaults.
    """
    lines = []
    header = "BSSID | SSID | RSSI | FREQ | TIMESTAMP"
    lines.append(header)
    lines.append('-' * len(header))

    for r in records:
        bssid = str(r.get('bssid', ''))
        ssid = str(r.get('ssid', ''))
        rssi = str(r.get('rssi', ''))
        freq = str(r.get('freq', r.get('channel', '')))
        ts = r.get('timestamp')
        if ts is None:
            # fallback to current unix timestamp
            ts = int(time.time())
        lines.append(f"{bssid} | {ssid} | {rssi} | {freq} | {ts}")

    return '\n'.join(lines)


def demo() -> None:
    sample = [
        {'bssid':'e0:bb:0c:32:d9:e3','ssid':'Mirliano-5G','rssi':-92,'freq':5220,'timestamp':1107708416},
        {'bssid':'1c:bd:b9:2a:82:e6','ssid':'kadastrpravo','rssi':-82,'freq':2457,'timestamp':1107707771},
        {'bssid':'76:e2:ea:45:b9:e6','ssid':'Galaxy A73 5G 574C','rssi':-67,'freq':2462,'timestamp':1107707899},
        {'bssid':'04:bf:6d:82:05:88','ssid':'HobbyGames','rssi':-72,'freq':2452,'timestamp':1107707684},
        {'bssid':'b4:b0:24:0f:1e:10','ssid':'SV295','rssi':-69,'freq':2462,'timestamp':1107707892},
        {'bssid':'d8:44:89:cd:a7:c6','ssid':'TP-Link_A7C6','rssi':-66,'freq':2462,'timestamp':1107707888},
        {'bssid':'0c:ef:15:24:10:2e','ssid':'SGW','rssi':-71,'freq':2417,'timestamp':1107706982},
        {'bssid':'f8:f0:82:cb:62:3a','ssid':'UDC_Korolev','rssi':-67,'freq':2422,'timestamp':1107707104},
        {'bssid':'40:3f:8c:89:26:7c','ssid':'Exlusivo','rssi':-77,'freq':2417,'timestamp':1107706985},
        {'bssid':'50:ff:20:8e:c1:c0','ssid':'Rubicone291','rssi':-56,'freq':2432,'timestamp':1107707297},
        {'bssid':'f8:f0:82:cb:62:3b','ssid':'UDC_Korolev','rssi':-87,'freq':5220,'timestamp':1107708416},
        {'bssid':'52:ff:20:8e:c1:c0','ssid':'Rubicone291','rssi':-67,'freq':5180,'timestamp':1107708216},
        {'bssid':'50:ff:20:79:5b:7e','ssid':'Rubicone','rssi':-68,'freq':2457,'timestamp':1107707801},
        {'bssid':'18:fd:74:33:50:d1','ssid':'Academia_TOP','rssi':-69,'freq':2452,'timestamp':1107701513},
        {'bssid':'b4:b0:24:0f:1e:0f','ssid':'SV295_5G','rssi':-86,'freq':5180,'timestamp':1107708209},
        {'bssid':'9c:53:22:52:d4:ee','ssid':'poddon_5G','rssi':-77,'freq':5200,'timestamp':1107708303},
        {'bssid':'9c:53:22:52:d4:ec','ssid':'poddon','rssi':-65,'freq':2422,'timestamp':1107707110},
        {'bssid':'50:ff:20:79:5b:80','ssid':'Rubicone','rssi':-53,'freq':5745,'timestamp':1107701257},
    ]
    print(format_records(sample))


if __name__ == '__main__':
    demo()
