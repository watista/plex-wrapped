"""Generate device icon mappings for static/js/device-icons.js.

Copy data/known_devices.json.example to data/known_devices.json after exporting
players from GET /admin/devices (or edit the example by hand).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEVICES_JSON = ROOT / "data" / "known_devices.json"
OUTPUT = ROOT / "static" / "js" / "device-icons.js"

CATEGORY_ICONS = {
    "iphone": "phone_iphone",
    "ipad": "tablet_mac",
    "android_phone": "phone_android",
    "android_tablet": "tablet_android",
    "tv": "tv",
    "apple_tv": "connected_tv",
    "chromecast": "cast",
    "streaming_box": "settings_input_hdmi",
    "browser": "language",
    "browser_safari": "public",
    "browser_unknown": "web",
    "windows": "desktop_windows",
    "mac": "laptop_mac",
    "playstation": "sports_esports",
    "roku": "live_tv",
    "generic": "devices",
}

CATEGORY_SILHOUETTE = {
    "iphone": "phone",
    "ipad": "tablet",
    "android_phone": "phone",
    "android_tablet": "tablet",
    "tv": "tv",
    "apple_tv": "tv",
    "chromecast": "cast",
    "streaming_box": "cast",
    "browser": "desktop",
    "browser_safari": "desktop",
    "browser_unknown": "desktop",
    "windows": "desktop",
    "mac": "desktop",
    "playstation": "console",
    "roku": "tv",
    "generic": "tv",
}

DEVICE_GROUPS: dict[str, list[str]] = {
    "iphone": [
        "iPhone",
        "iPhone van Alex",
        "iPhone 11 Pro Max",
        "iPhone van Sam",
        "iPhone van Jordan",
        "iPhone van Riley",
        "iPhone (2)",
        "Alex's iPhone",
        "iPhone van Morgan",
        "iPhone van Casey",
    ],
    "ipad": [
        "iPad",
        "iPad van Alex",
        "iPad van Sam (2)",
        "iPad Pro van Jordan",
        "iPad van Riley",
    ],
    "apple_tv": [
        "Apple TV",
        "Apple\u00a0TV",
        "Woonkamer",
        "Hoofdslaapkamer",
        "Slaapkamer",
    ],
    "chromecast": [
        "Chromecast",
        "Chromecast Google TV",
        "Chromecast Google TV (HD)",
        "Chromecast HD",
        "Google TV Streamer",
    ],
    "browser": [
        "Chrome",
        "Microsoft Edge",
        "Firefox",
        "Opera",
        "Vivaldi",
        "Plex Web (Chrome)",
    ],
    "browser_safari": ["Safari", "Plex Web (Safari)"],
    "browser_unknown": ["Unknown Browser", "Plex Web (Unknown Browser)"],
    "tv": [
        "LG OLED55C16LA",
        "LG 43UJ630V-ZA",
        "TV 2020",
        "BRAVIA 4K GB",
        "Philips UHD Android TV",
        "Plex for LG",
        "Plex for Smart TVs",
    ],
    "android_phone": [
        "Galaxy S24 Ultra",
        "Alex's S22",
        "SM-G781B",
        "OnePlus Nord 4",
        "Galaxy S9",
        "OnePlus 7 Pro",
        "Nothing Phone (2a)",
        "Galaxy S10",
        "Pixel 9 Pro XL",
        "123456789",
        "Telefoon van Sam",
        "SM-G973F",
        "moto g14",
        "Pixel 8",
    ],
    "android_tablet": [
        "Galaxy Tab S7+",
        "Alex's Galaxy Tab S7+",
        "Galaxy Tab S9",
        "Galaxy Tab S7 FE",
        "SM-T830",
        "Galaxy Tab S10 FE 5G",
    ],
    "playstation": [
        "PlayStation 4",
        "PlayStation 4 Pro",
        "Plex for PlayStation 4",
        "PS4-856",
        "PS5-979",
    ],
    "windows": [
        "DESKTOP-EXAMPLE01",
        "LAPTOP-DEMO02",
        "Philips-PC",
    ],
    "mac": ["MBP Demo", "MacBook Air van Alex"],
    "streaming_box": [
        "4K TV Box",
        "KPN TV+ Box",
        "KPN DIW7022",
    ],
    "roku": ["Sam's TV"],
    "generic": ["Generic"],
}


def classify_by_name(name: str) -> str:
    lower = (name or "").strip().lower()
    if not lower:
        return "generic"

    if re.search(r"playstation|ps[345]-|plex for (sony|playstation)", lower):
        return "playstation"
    if re.search(r"apple\s*tv", name, re.I):
        return "apple_tv"
    if re.search(r"chromecast|google tv streamer", lower):
        return "chromecast"
    if lower == "safari" or "plex web (safari)" in lower:
        return "browser_safari"
    if "unknown browser" in lower or "plex web (unknown browser)" in lower:
        return "browser_unknown"
    if lower in {"chrome", "microsoft edge", "firefox", "opera", "vivaldi"} or "plex web" in lower:
        return "browser"
    if "ipad" in lower:
        return "ipad"
    if "iphone" in lower:
        return "iphone"
    if re.search(r"galaxy tab|tab s\d|tab s10|sm-t\d|\btablet\b", lower):
        return "android_tablet"
    if re.search(
        r"^tv 20|^tv ue|^tv qe|bravia|(?:^|\s)lg |philips uhd|philips google|hisense|mitv|"
        r"4k.*tv|smart tv|plex for lg|plex for smart|nano|oled|uj\d|um\d|uh\d|qned|sk\d|ef\d|ur\d",
        lower,
    ):
        return "tv"
    if "'s tv" in lower or "roku" in lower:
        return "roku"
    if re.search(r"kpn|tv box|tv\+ box|hdmi|pov_tv|qm\d|tp\d|xk03|ai pont|4k tv box", lower):
        return "streaming_box"
    if re.search(r"^desktop-|^laptop-|philips-pc", lower):
        return "windows"
    if re.search(r"macbook|^mbp ", lower):
        return "mac"
    if re.search(
        r"galaxy|oneplus|pixel|sm-[gsaxt]|honor|huawei|nothing phone|moto |p8 lite|p20|flare|"
        r"telefoon|ablet|30x|ate\?|^st$|^4t$|123456789|in20|kb20|eb21|cph|mi\s+\d",
        lower,
    ):
        return "android_phone"
    return "generic"


def build_mapping(devices: list[dict] | None = None) -> dict[str, dict[str, str]]:
    mapping: dict[str, dict[str, str]] = {}
    for category, names in DEVICE_GROUPS.items():
        for name in names:
            mapping[name] = {
                "category": category,
                "icon": CATEGORY_ICONS[category],
                "silhouette": CATEGORY_SILHOUETTE[category],
            }

    if devices:
        for device in devices:
            name = device["name"]
            if name not in mapping:
                category = classify_by_name(name)
                mapping[name] = {
                    "category": category,
                    "icon": CATEGORY_ICONS[category],
                    "silhouette": CATEGORY_SILHOUETTE[category],
                }
    return mapping


def render_js() -> str:
    groups_json = json.dumps(DEVICE_GROUPS, ensure_ascii=False, indent=2)
    icons_json = json.dumps(CATEGORY_ICONS, indent=2)
    silhouettes_json = json.dumps(CATEGORY_SILHOUETTE, indent=2)
    return f"""/* Generated by scripts/generate_device_icons.py — do not edit by hand. */
(function (global) {{
  const CATEGORY_ICONS = {icons_json};

  const CATEGORY_SILHOUETTE = {silhouettes_json};

  const DEVICE_GROUPS = {groups_json};

  const DEVICE_BY_NAME = {{}};
  for (const [category, names] of Object.entries(DEVICE_GROUPS)) {{
    for (const name of names) {{
      DEVICE_BY_NAME[name] = {{
        category,
        icon: CATEGORY_ICONS[category] || CATEGORY_ICONS.generic,
      }};
    }}
  }}

  function classifyByName(name) {{
    const lower = (name || "").trim().toLowerCase();
    if (!lower) return "generic";

    if (/playstation|ps[345]-|plex for (sony|playstation)/.test(lower)) {{
      return "playstation";
    }}
    if (/apple\\s*tv/.test(name)) return "apple_tv";
    if (/chromecast|google tv streamer/.test(lower)) return "chromecast";
    if (lower === "safari" || lower.includes("plex web (safari)")) return "browser_safari";
    if (lower.includes("unknown browser") || lower.includes("plex web (unknown browser)")) {{
      return "browser_unknown";
    }}
    if (
      lower === "chrome" ||
      lower === "microsoft edge" ||
      lower === "firefox" ||
      lower === "opera" ||
      lower === "vivaldi" ||
      lower.includes("plex web")
    ) {{
      return "browser";
    }}
    if (/ipad/.test(lower)) return "ipad";
    if (/iphone/.test(lower)) return "iphone";
    if (/galaxy tab|tab s\\d|tab s10|sm-t\\d|\\btablet\\b/.test(lower)) return "android_tablet";
    if (
      /^tv 20|^tv ue|^tv qe|bravia|(?:^|\\s)lg |philips uhd|philips google|hisense|mitv|4k.*tv|smart tv|plex for lg|plex for smart|nano|oled|uj\\d|um\\d|uh\\d|qned|sk\\d|ef\\d|ur\\d/.test(
        lower
      )
    ) {{
      return "tv";
    }}
    if (/\\'s tv|roku/.test(lower)) return "roku";
    if (/kpn|tv box|tv\\+ box|hdmi|pov_tv|qm\\d|tp\\d|xk03|ai pont|4k tv box/.test(lower)) {{
      return "streaming_box";
    }}
    if (/^desktop-|^laptop-|philips-pc/.test(lower)) return "windows";
    if (/macbook|^mbp /.test(lower)) return "mac";
    if (
      /galaxy|oneplus|pixel|sm-[gsaxt]|honor|huawei|nothing phone|moto |p8 lite|p20|flare|telefoon|ablet|30x|ate\\?|^st$|^4t$|123456789|in20|kb20|eb21|cph|mi\\s+\\d/.test(
        lower
      )
    ) {{
      return "android_phone";
    }}
    return "generic";
  }}

  function resolveDeviceIcon(name) {{
    const trimmed = (name || "").trim();
    if (!trimmed) {{
      return {{
        icon: CATEGORY_ICONS.generic,
        category: "generic",
        silhouette: CATEGORY_SILHOUETTE.generic,
      }};
    }}

    const mapped = DEVICE_BY_NAME[trimmed];
    const category = mapped ? mapped.category : classifyByName(trimmed);
    const icon = mapped ? mapped.icon : CATEGORY_ICONS[category] || CATEGORY_ICONS.generic;
    const silhouette = CATEGORY_SILHOUETTE[category] || CATEGORY_SILHOUETTE.generic;

    return {{ icon, category, silhouette }};
  }}

  global.DeviceIcons = {{
    resolve: resolveDeviceIcon,
    byName: DEVICE_BY_NAME,
    icons: CATEGORY_ICONS,
  }};
}})(typeof window !== "undefined" ? window : globalThis);
"""


def main() -> None:
    if not DEVICES_JSON.is_file():
        example = ROOT / "data" / "known_devices.json.example"
        raise SystemExit(
            f"Missing {DEVICES_JSON.relative_to(ROOT)} — copy {example.relative_to(ROOT)} and edit, "
            "or save GET /admin/devices output to that path."
        )
    devices = json.loads(DEVICES_JSON.read_text(encoding="utf-8"))["devices"]
    mapping = build_mapping(devices)
    OUTPUT.write_text(render_js(), encoding="utf-8")
    print(f"Wrote device icon mappings ({len(mapping)} devices) to {OUTPUT}")


if __name__ == "__main__":
    main()
