"""渠道码表初始数据：(code, name_zh, country, category, note, sort_order)。"""

from __future__ import annotations

# 大类：空运 / 海运 / 快递 / 卡航 / 铁路
CHANNEL_CATEGORIES: tuple[str, ...] = ("空运", "海运", "快递", "卡航", "铁路")

CHANNEL_SEEDS: list[tuple[str, str, str, str, str, int]] = [
    ("Sea Truck Standard Service - LAX", "美国普船", "美国", "海运", "", 10),
    ("Sea Truck Rapid Service - LAX", "美国快船", "美国", "海运", "", 20),
    ("Air Express Economy Service", "美国空运", "美国", "空运", "", 30),
    ("Canada Fast sea truck", "加拿大快船", "加拿大", "海运", "", 40),
    ("European Sea truck  DDP", "欧洲海运", "欧洲", "海运", "", 60),
    ("Canada Sea truck", "加拿大普船", "加拿大", "海运", "", 70),
    ("Sea Express Guaranteed Service - LAX", "美国普船", "美国", "海运", "", 80),
    ("Sea Express Rapid Service - LAX", "美国快船", "美国", "海运", "", 90),
    ("USA Sea truck", "美国普船", "美国", "海运", "", 100),
    ("Sea Express Standard Service - LAX", "美国普船", "美国", "海运", "", 110),
    ("UK Air Express DDP", "英国空运", "英国", "空运", "", 130),
    ("UK Sea truck  DDP", "英国海运", "英国", "海运", "", 50),
    ("UK Sea truck  DDU", "英国海运", "英国", "海运", "", 260),
    ("UK Sea Express  DDP", "英国海运", "英国", "海运", "", 120),
    ("Canada Fast sea express", "加拿大快船", "加拿大", "海运", "", 140),
    ("Sea Truck Economy Service - CHIZT", "美国普船", "美国", "海运", "", 150),
    ("AU Sea express", "澳大利亚海运", "澳大利亚", "海运", "", 160),
    ("European Air Express DDP", "欧洲空运", "欧洲", "空运", "", 170),
    ("European Sea Express  DDP", "欧洲海运", "欧洲", "海运", "", 180),
    ("AU sea truck", "澳大利亚海运", "澳大利亚", "海运", "", 190),
    ("Canada Air express", "加拿大空运", "加拿大", "空运", "", 200),
    ("European Road Express  DDP", "欧洲卡航", "欧洲", "卡航", "", 210),
    ("Mexico sea truck", "墨西哥海运", "墨西哥", "海运", "", 220),
    ("European Road truck  DDU", "欧洲卡航", "欧洲", "卡航", "", 230),
    ("European Sea truck  DDU", "欧洲海运", "欧洲", "海运", "", 240),
    ("AU Air express", "澳大利亚空运", "澳大利亚", "空运", "", 250),
    ("Canada Sea Express", "加拿大普船", "加拿大", "海运", "", 270),
]
