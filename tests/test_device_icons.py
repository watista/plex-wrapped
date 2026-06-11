from __future__ import annotations

import json
from pathlib import Path

from scripts.generate_device_icons import build_mapping

KNOWN_DEVICES = Path(__file__).resolve().parents[1] / "data" / "known_devices.json"


def test_all_known_devices_have_icon_mapping():
    payload = json.loads(KNOWN_DEVICES.read_text(encoding="utf-8"))
    mapping = build_mapping(payload["devices"])

    assert len(mapping) == payload["count"]
    for device in payload["devices"]:
        name = device["name"]
        assert name in mapping, f"missing mapping for {name!r}"
        meta = mapping[name]
        assert meta["category"]
        assert meta["icon"]


def test_device_icon_examples():
    mapping = build_mapping(json.loads(KNOWN_DEVICES.read_text(encoding="utf-8"))["devices"])

    assert mapping["iPhone"]["icon"] == "phone_iphone"
    assert mapping["LG OLED55C16LA"]["icon"] == "tv"
    assert mapping["Chromecast"]["icon"] == "cast"
    assert mapping["Apple TV"]["icon"] == "connected_tv"
    assert mapping["Woonkamer"]["icon"] == "connected_tv"
    assert mapping["PlayStation 4"]["icon"] == "sports_esports"
    assert mapping["Safari"]["icon"] == "public"
    assert mapping["Chrome"]["icon"] == "language"
    assert mapping["Galaxy Tab S7+"]["icon"] == "tablet_android"
    assert mapping["Sarah's TV"]["icon"] == "live_tv"
