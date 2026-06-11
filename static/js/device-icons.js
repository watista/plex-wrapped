(function (global) {
  const CATEGORY_ICONS = {
    iphone: "phone_iphone",
    ipad: "tablet_mac",
    android_phone: "phone_android",
    android_tablet: "tablet_android",
    tv: "tv",
    apple_tv: "connected_tv",
    chromecast: "cast",
    streaming_box: "settings_input_hdmi",
    browser: "language",
    browser_safari: "public",
    browser_unknown: "web",
    windows: "desktop_windows",
    mac: "laptop_mac",
    playstation: "sports_esports",
    roku: "live_tv",
    generic: "devices",
  };

  const CATEGORY_SILHOUETTE = {
    iphone: "phone",
    ipad: "tablet",
    android_phone: "phone",
    android_tablet: "tablet",
    tv: "tv",
    apple_tv: "tv",
    chromecast: "cast",
    streaming_box: "cast",
    browser: "desktop",
    browser_safari: "desktop",
    browser_unknown: "desktop",
    windows: "desktop",
    mac: "desktop",
    playstation: "console",
    roku: "tv",
    generic: "tv",
  };

  const DEVICE_GROUPS = {
    iphone: [
      "iPhone",
      "iPhone van Sophie",
      "Iphone 11 pro max",
      "iPhone van Lindy",
      "iPhone van Julia",
      "iPhone van Elise Vriesema",
      "iPhone van Wouter",
      "iPhone van Kevin",
      "iPhone van mirte",
      "iPhone van Sebastian",
      "iPhone van Nikki",
      "iPhone van Alicia",
      "iPhone van Niels",
      "iPhone van RJ",
      "iPhone van Yvonne",
      "Je boi",
      "iPhone van Anoniem",
      "iPhone van Manh Tuong",
      "iPhone van Maruja",
      "iPhone van Rick (2)",
      "iPhone (4)",
      "iPhone George",
      "iPhone van Anouk",
      "iPhone van Dominique",
      "iPhone van Jilco",
      "iPhone van Van-Nhi",
      "E\u2019s iPhone",
      "iPhone renske",
      "iPhone van D.",
      "iPhone van George",
      "iPhone van Joey",
      "iPhone van Marloes",
      "Iphone k",
      "Philip\u2019s iPhone",
      "Bernardina",
      "Luca NT",
      "Luca Ching phou",
      "Alleen voor dikke tantoes",
      "andy",
      "GPW 1942",
      "Nikki Ysendoorn",
      "iPhone van Eva (2)",
      "iPhone van Wesley",
    ],
    ipad: [
      "iPad",
      "iPad van Bianca",
      "iPad van Ad (2)",
      "iPad van Inge",
      "iPad van Ad",
      "iPad van Bianca (2)",
      "iPad van Kimberly",
      "iPad van Nikki",
      "iPad van Maruja",
      "iPad van Nadia",
      "iPad van Ngoc (2)",
      "iPad Pro van George",
      "iPad van Ann Paas",
      "iPad van Cindy",
      "iPad van H",
      "iPad van Romy",
    ],
    apple_tv: [
      "Apple TV Nikki",
      "Woonkamer",
      "Hoofdslaapkamer",
      "Slaapkamer",
      "Apple TV",
      "Apple\u00a0TV",
    ],
    chromecast: [
      "Chromecast",
      "Chromecast Google TV",
      "Chromecast Google TV (HD)",
      "Chromecast HD",
      "Google TV Streamer",
    ],
    browser: [
      "Chrome",
      "Microsoft Edge",
      "Firefox",
      "Opera",
      "Vivaldi",
      "Plex Web (Chrome)",
    ],
    browser_safari: ["Safari", "Plex Web (Safari)"],
    browser_unknown: ["Unknown Browser", "Plex Web (Unknown Browser)"],
    tv: [
      "LG 43UJ630V-ZA",
      "LG 55NANO956NA",
      "TV 2020",
      "4K Ultra Slim LED TV powered by Android",
      "BRAVIA 4K GB",
      "TV 2019",
      "LG OLED55C16LA",
      "TV 2024",
      "TV 2021",
      "Smart TV Pro",
      "LG OLED55C8PLA",
      "TV 2018",
      "4K UHD Razor Slim LED TV powered by Android\u2122",
      "LG OLED55CS6LA",
      "LG 43UM7100PLB",
      "Philips UHD Android TV",
      "LG 65SK8000PLB",
      "TV QE55Q9FNA",
      "BRAVIA 4K GB ATV3",
      "TV 2022",
      "TV UE55NU7102",
      "LG 55EF950V-ZA",
      "Plex for LG",
      "LG OLED65B8PLA",
      "4K LED TV powered by Android",
      "TV 2025",
      "TV QE75Q900R",
      "LG OLED65C16LA",
      "BRAVIA 4K 2015",
      "LG OLED55C9PLA",
      "TV UE50RU7170SXXN",
      "LG 49UJ630V-ZA",
      "TV 2023",
      "LG 55UH615V-ZB",
      "TV UE40F5500",
      "TV UE55NU8000",
      "BRAVIA 2015",
      "LG OLED65B26LA",
      "Plex for Smart TVs",
      "TV UE43NU7090",
      "TV UE55KU6470",
      "LG 50QNED82A6B.AEUU6JP",
      "LG OLED55C12LA",
      "MiTV-AESP0",
      "TV UE40ES5500",
      "LG OLED55CX6LA",
      "Philips Google TV TA1",
      "TV UE40F7000",
      "TV UE50JU6400",
      "Hisense 58A53FEVS_0010",
      "LG 43UR73003LA",
      "TV UE65HU7500",
      "TV 2017",
      "LG 55UH605V-ZC",
    ],
    android_phone: [
      "Galaxy S20 FE",
      "Oscar's S22",
      "SM-G781B",
      "XK03H",
      "S20 FE van stijn",
      "P8 Lite",
      "OnePlus Nord 4",
      "Galaxy S9",
      "SM-S901B",
      "OnePlus 7 Pro",
      "Galaxy S24 Ultra",
      "OnePlus 6",
      "A52s van Danny",
      "M2012K11AG",
      "Jeff's Galaxy",
      "OnePlus 10 Pro 5G",
      "ONEPLUS A3003",
      "Galaxy A52s 5G",
      "Galaxy A54 5G",
      "S23 van Carina",
      "Nothing Phone (2a)",
      "NE2213",
      "Galaxy S10",
      "Victoria's A52s",
      "Galaxy S8",
      "Honor 10",
      "ONEPLUS A5000",
      "Galaxy A5(2016)",
      "Pixel 9 Pro XL",
      "HUAWEI P7-L10",
      "ST",
      "A54 van Elzo",
      "Galaxy A51",
      "Galaxy S20 FE 5G",
      "Galaxy S8+",
      "Galaxy A50",
      "Galaxy S10e",
      "S24 van Ruud",
      "Stijn 1+8P",
      "Galaxy A56 5G",
      "Galaxy S10+",
      "Galaxy S23 Ultra",
      "P20 lite",
      "123456789",
      "Flare J2 Max",
      "Galaxy S23",
      "Job's S23 Ultra",
      "KB2003",
      "SM-A505FN",
      "ablet (M700C)",
      "DESKTOP-CD90VUV",
      "EB2103",
      "moto g14",
      "Pixel 3a",
      "S24+ van fokke",
      "SM-G973F",
      "Telefoon van Rixt",
      "30X",
      "A50 van Danny",
      "A70 van Michel",
      "CPH2145",
      "Danny's S25 FE",
      "Galaxy S20",
      "Galaxy S20+ 5G",
      "Galaxy S23+",
      "IN2013",
      "IN2023",
      "MI  8  Pro",
      "ONEPLUS A6013",
      "Pixel 8",
      "S24 Ultra van Daan",
      "SM-G975F",
      "SM-G981B",
      "SM-X900",
      "Galaxy A3(2016)",
      "4T",
      "Bharat Go",
      "ate? 2",
      "TPM191E",
      "TPM171E",
      "QM164E",
    ],
    android_tablet: [
      "Galaxy Tab S7+",
      "Oscar's Galaxy Tab S7+",
      "Galaxy Tab A (2016)",
      "Tab S7 FE van Danny",
      "SM-T830",
      "Naomie's Tab S9",
      "Galaxy Tab S9",
      "Galaxy Tab S7 FE",
      "SM-T733",
      "Galaxy Tab S10 FE 5G",
      "SM-T800",
      "Tab S10+ van Familie",
    ],
    playstation: [
      "Plex for Sony (PlayStation 3 01.41)",
      "PS4-856",
      "PS5-979",
      "PlayStation 4",
      "Plex for PlayStation 4",
      "PlayStation 4 Pro",
      "PS4-727",
      "PS5-220",
      "PS4-102",
      "PS4-137",
      "PS5-401",
    ],
    windows: [
      "DESKTOP-GGB57TM",
      "LAPTOP-JBO8NIJB",
      "LAPTOP-ALPS2QKH",
      "DESKTOP-875R8T1",
      "LAPTOP-JUUKH042",
      "LAPTOP-LH33S4TQ",
      "DESKTOP-3TR2QI7",
      "Philips-PC",
    ],
    mac: ["MBP Stijn", "MacBook Air van Eva"],
    streaming_box: [
      "4K TV Box",
      "POV_TV-HDMI-200BT(V2.0)",
      "KPN TV+ Box",
      "KPN DIW7022",
      "AI PONT",
    ],
    roku: ["Sarah's TV"],
    generic: ["Generic"],
  };

  const DEVICE_BY_NAME = {};
  for (const [category, names] of Object.entries(DEVICE_GROUPS)) {
    for (const name of names) {
      DEVICE_BY_NAME[name] = {
        category,
        icon: CATEGORY_ICONS[category] || CATEGORY_ICONS.generic,
      };
    }
  }

  function classifyByName(name) {
    const lower = (name || "").trim().toLowerCase();
    if (!lower) return "generic";

    if (/playstation|ps[345]-|plex for (sony|playstation)/.test(lower)) {
      return "playstation";
    }
    if (/apple\s*tv/.test(name)) return "apple_tv";
    if (/chromecast|google tv streamer/.test(lower)) return "chromecast";
    if (lower === "safari" || lower.includes("plex web (safari)")) return "browser_safari";
    if (lower.includes("unknown browser") || lower.includes("plex web (unknown browser)")) {
      return "browser_unknown";
    }
    if (
      lower === "chrome" ||
      lower === "microsoft edge" ||
      lower === "firefox" ||
      lower === "opera" ||
      lower === "vivaldi" ||
      lower.includes("plex web")
    ) {
      return "browser";
    }
    if (/ipad/.test(lower)) return "ipad";
    if (/iphone/.test(lower)) return "iphone";
    if (/galaxy tab|tab s\d|tab s10|sm-t\d|\btablet\b/.test(lower)) return "android_tablet";
    if (
      /^tv 20|^tv ue|^tv qe|bravia|(?:^|\s)lg |philips uhd|philips google|hisense|mitv|4k.*tv|smart tv|plex for lg|plex for smart|nano|oled|uj\d|um\d|uh\d|qned|sk\d|ef\d|ur\d/.test(
        lower
      )
    ) {
      return "tv";
    }
    if (/sarah's tv/.test(lower)) return "roku";
    if (/kpn|tv box|tv\+ box|hdmi|pov_tv|qm\d|tp\d|xk03|ai pont|4k tv box/.test(lower)) {
      return "streaming_box";
    }
    if (/^desktop-|^laptop-|philips-pc/.test(lower)) return "windows";
    if (/macbook|^mbp /.test(lower)) return "mac";
    if (
      /galaxy|oneplus|pixel|sm-[gsaxt]|honor|huawei|nothing phone|moto |p8 lite|p20|flare|telefoon|jeff|bharat|ablet|30x|ate\?|^st$|^4t$|123456789|in20|kb20|eb21|cph|mi\s+\d/.test(
        lower
      )
    ) {
      return "android_phone";
    }
    return "generic";
  }

  function resolveDeviceIcon(name) {
    const trimmed = (name || "").trim();
    if (!trimmed) {
      return {
        icon: CATEGORY_ICONS.generic,
        category: "generic",
        silhouette: CATEGORY_SILHOUETTE.generic,
      };
    }

    const mapped = DEVICE_BY_NAME[trimmed];
    const category = mapped ? mapped.category : classifyByName(trimmed);
    const icon = mapped ? mapped.icon : CATEGORY_ICONS[category] || CATEGORY_ICONS.generic;
    const silhouette = CATEGORY_SILHOUETTE[category] || CATEGORY_SILHOUETTE.generic;

    return { icon, category, silhouette };
  }

  global.DeviceIcons = {
    resolve: resolveDeviceIcon,
    byName: DEVICE_BY_NAME,
    icons: CATEGORY_ICONS,
  };
})(typeof window !== "undefined" ? window : globalThis);
