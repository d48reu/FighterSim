"""Locale-based name generation with romanized fallbacks for non-Latin scripts.

Maps ~20 MMA-prominent nationalities to Faker locales. Non-Latin locales
(Russian, Dagestani, South Korean, Georgian) use hardcoded romanized name
arrays. Japanese uses Faker's built-in romanized_name() method.

All generated names are Latin-script only.
"""

import random
import unicodedata

from faker import Faker


# Special character replacements that NFD decomposition doesn't handle
_SPECIAL_CHARS: dict[str, str] = {
    "\u00f8": "o",  # ø -> o (Norwegian/Danish)
    "\u00d8": "O",  # Ø -> O
    "\u00e6": "ae", # æ -> ae
    "\u00c6": "AE", # Æ -> AE
    "\u00f0": "d",  # ð -> d (Icelandic eth)
    "\u00d0": "D",  # Ð -> D
    "\u00fe": "th", # þ -> th (Icelandic thorn)
    "\u00de": "TH", # Þ -> TH
    "\u0142": "l",  # ł -> l (Polish)
    "\u0141": "L",  # Ł -> L
    "\u00df": "ss", # ß -> ss (German)
    "\u0111": "d",  # đ -> d (Croatian)
    "\u0110": "D",  # Đ -> D
}


def _to_ascii(name: str) -> str:
    """Strip diacritics and special characters, producing ASCII-only output.

    Handles both standard diacritics (via NFD decomposition) and special
    characters like ø, æ, ł, ß that don't decompose cleanly.
    """
    # First pass: replace special characters that NFD can't handle
    for char, replacement in _SPECIAL_CHARS.items():
        name = name.replace(char, replacement)
    # Second pass: decompose remaining diacritics and strip combining marks
    nfkd = unicodedata.normalize("NFKD", name)
    return "".join(c for c in nfkd if not unicodedata.combining(c))

# ---------------------------------------------------------------------------
# Latin-script Faker locales
# ---------------------------------------------------------------------------

NATIONALITY_LOCALE_MAP: dict[str, str] = {
    "American": "en_US",
    "Brazilian": "pt_BR",
    "Mexican": "es_MX",
    "Irish": "en_IE",
    "British": "en_GB",
    "Canadian": "en_CA",
    "Australian": "en_AU",
    "Swedish": "sv_SE",
    "Norwegian": "no_NO",
    "Polish": "pl_PL",
    "Dutch": "nl_NL",
    "French": "fr_FR",
    "German": "de_DE",
    "Nigerian": "en_NG",
    "South African": "zu_ZA",
    "New Zealander": "en_NZ",
    "Cameroonian": "fr_FR",   # proxy: French-speaking country
    "Jamaican": "en_GB",      # proxy: English-speaking Caribbean
    "Japanese": "ja_JP",      # uses romanized_name() method
}

# ---------------------------------------------------------------------------
# Romanized name lists for non-Latin locales
# ---------------------------------------------------------------------------

ROMANIZED_NAMES: dict[str, dict[str, list[str]]] = {
    "Russian": {
        "first": [
            "Aleksandr", "Dmitri", "Sergei", "Andrei", "Pavel", "Nikolai",
            "Artem", "Magomed", "Petr", "Maksim", "Viktor", "Ivan", "Oleg",
            "Yuri", "Vladislav", "Roman", "Anton", "Mikhail", "Kirill",
            "Valentin", "Ruslan", "Timur", "Fedor", "Ilya", "Stanislav",
            "Boris", "Gennadi", "Alexei", "Vitali", "Denis", "Konstantin",
            "Evgeni", "Vadim", "Georgi", "Igor", "Anatoli", "Leonid",
            "Nikita", "Rostislav", "Stepan", "Yaroslav", "Zakhar", "Matvei",
            "Danila", "Bogdan", "Lev", "Vasili", "Gleb", "Mark", "Semyon",
            "Egor", "Timofei", "Daniil",
        ],
        "last": [
            "Volkov", "Petrov", "Ivanov", "Morozov", "Sokolov", "Fedorov",
            "Kuznetsov", "Popov", "Lebedev", "Kozlov", "Novikov", "Smirnov",
            "Pavlov", "Orlov", "Zhukov", "Romanov", "Vasiliev", "Kovalev",
            "Emelianenko", "Shlemenko", "Kharitonov", "Minakov", "Nemkov",
            "Moldavsky", "Tokov", "Ismailov", "Bogatov", "Tsarukyan",
            "Ankalaev", "Emeev", "Lozhkin", "Frolov", "Sidorov", "Zaitsev",
            "Grigoriev", "Tarasov", "Belov", "Vinogradov", "Nikitin",
            "Makarov", "Gusev", "Titov", "Kuzmin", "Baranov", "Polyakov",
            "Chernov", "Vlasov", "Komarov", "Zubkov", "Medvedev",
            "Golubev", "Davydov",
        ],
    },
    "Dagestani": {
        "first": [
            "Khabib", "Islam", "Zabit", "Magomed", "Shamil", "Abdulmanap",
            "Abubakar", "Makhach", "Gamzat", "Rasul", "Murad", "Akhmed",
            "Saygid", "Magomedrasul", "Rustam", "Alibek", "Gadzhimurad",
            "Khalid", "Tagir", "Kamil", "Said", "Ramazan", "Usman",
            "Abdulrashid", "Gadzhi", "Magomedsaid", "Nurmagomed", "Tamerlan",
            "Kurban", "Ibragim", "Idris", "Gadzhidaud", "Abdulkadir",
            "Eldar", "Suleiman", "Bilal", "Hamzat", "Shakhban", "Arsen",
            "Muslim", "Apti", "Batal", "Dzhamal", "Isa", "Mairbek",
            "Rizvan", "Sukhrab", "Timur", "Zelim", "Aslan",
            "Daud", "Mansur",
        ],
        "last": [
            "Nurmagomedov", "Makhachev", "Magomedsharipov", "Abdulkhabirov",
            "Saidov", "Magomedov", "Gasanov", "Isaev", "Alikhanov",
            "Abdulazizov", "Gamzatov", "Ramazanov", "Khasbulaev",
            "Omarov", "Gadzhiev", "Aliev", "Akhmedov", "Sultanakhmedov",
            "Magomedaliev", "Umalatov", "Taisumov", "Bibulatov", "Abdulaev",
            "Kadimagomaev", "Magomedkerimov", "Shamkhalov", "Kuramagomedov",
            "Tukhugov", "Salikhov", "Khabilov", "Mustafaev", "Aduev",
            "Daudov", "Gadzhidaudov", "Kubanov", "Gadzhiagaev",
            "Khalidov", "Abdurakhmanov", "Guseinov", "Magomedgadzhiev",
            "Kurbanov", "Shaburov", "Bakshaev", "Dzhabrailov", "Nasrulaev",
            "Mamedov", "Shakhbanov", "Ibragimov", "Akhmatov", "Kerimov",
            "Dibirov", "Sultanmuradov",
        ],
    },
    "South Korean": {
        "first": [
            "Sung-Jung", "Chan-Mi", "Dong-Hyun", "Kyung-Ho", "Doo-Ho",
            "Seung-Woo", "Hyun-Gyu", "Da-Un", "Min-Woo", "Ji-Yeon",
            "Tae-Hyun", "Jun-Young", "Sang-Won", "Myung-Hyun", "Kwon-Ho",
            "Soo-Chul", "Yong-Jin", "Hae-Sung", "Jin-Soo", "Jae-Young",
            "Byung-Kwan", "Kang-Woo", "Si-Woo", "Yeon-Sung", "Ho-Jun",
            "Woo-Jin", "Dae-Sung", "Sung-Min", "Young-Jae", "Hyun-Soo",
            "Dong-Sik", "Sung-Hwan",
        ],
        "last": [
            "Kim", "Park", "Lee", "Choi", "Jung", "Kang", "Yoon", "Jang",
            "Lim", "Han", "Oh", "Seo", "Shin", "Kwon", "Hwang", "Ahn",
            "Song", "Yoo", "Hong", "Moon", "Ryu", "Bae", "Cho",
        ],
    },
    "Georgian": {
        "first": [
            "Merab", "Giga", "Levan", "Giorgi", "Lasha", "Ilia",
            "Zurab", "Tornike", "Davit", "Guram", "Beka", "Nikoloz",
            "Revaz", "Vakhtang", "Archil", "Badri", "Gocha", "Kakha",
            "Malkhaz", "Nodar", "Otar", "Paata", "Ramaz", "Saba",
            "Tengiz", "Temur", "Vato", "Zaza", "Amiran", "Mamuka",
            "Bidzina", "Dato",
        ],
        "last": [
            "Dvalishvili", "Chikadze", "Machavariani", "Kutateladze",
            "Topuria", "Shavkatashvili", "Salukvadze", "Giorgadze",
            "Berishvili", "Tsintsadze", "Lomidze", "Kharabadze",
            "Chkheidze", "Javakhishvili", "Dolidze", "Kvirkvelia",
            "Margvelashvili", "Gamsakhurdia", "Tsiklauri", "Pirtskhalava",
            "Latsabidze", "Svanidze", "Tsereteli", "Zarandia",
            "Gabashvili", "Imerlishvili", "Khetaguri", "Natsvlishvili",
            "Tavadze", "Bakradze", "Nadiradze", "Grigalashvili",
        ],
    },
}

# ---------------------------------------------------------------------------
# Nationality distribution weights (MMA-realistic)
# ---------------------------------------------------------------------------

NATIONALITY_WEIGHTS: dict[str, float] = {
    # Big markets ~15-20%
    "American": 0.18,
    "Brazilian": 0.16,
    "Russian": 0.10,
    "Dagestani": 0.08,
    # Medium markets ~5-8%
    "British": 0.06,
    "Canadian": 0.05,
    "Irish": 0.04,
    "Mexican": 0.05,
    "Australian": 0.04,
    "Japanese": 0.04,
    "Polish": 0.03,
    # Small markets ~2-4%
    "Swedish": 0.02,
    "Norwegian": 0.02,
    "South Korean": 0.02,
    "Georgian": 0.02,
    "Dutch": 0.02,
    "French": 0.02,
    "German": 0.02,
    "Nigerian": 0.01,
    "Cameroonian": 0.01,
    "South African": 0.01,
    "New Zealander": 0.01,
    "Jamaican": 0.01,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def create_faker_instances(seed: int) -> dict[str, Faker]:
    """Create one Faker instance per unique locale, seeded deterministically.

    Returns dict keyed by locale code (e.g. "en_US", "pt_BR").
    """
    Faker.seed(seed)
    instances: dict[str, Faker] = {}
    for locale in sorted(set(NATIONALITY_LOCALE_MAP.values())):
        instances[locale] = Faker(locale)
    return instances


def generate_name(
    nationality: str,
    faker_instances: dict[str, Faker],
    rng: random.Random,
    used_names: set[str],
) -> str:
    """Generate a unique Latin-script name matching the fighter's nationality.

    Args:
        nationality: One of the keys in NATIONALITY_LOCALE_MAP or ROMANIZED_NAMES,
                     or "Japanese".
        faker_instances: Dict from create_faker_instances().
        rng: Seeded stdlib random.Random for deterministic choice.
        used_names: Mutable set tracking already-used names (modified in-place).

    Returns:
        A unique "First Last" name string, Latin-script only.
    """
    for attempt in range(200):
        if nationality == "Japanese":
            raw = faker_instances["ja_JP"].romanized_name()
        elif nationality in ROMANIZED_NAMES:
            pool = ROMANIZED_NAMES[nationality]
            first = rng.choice(pool["first"])
            last = rng.choice(pool["last"])
            raw = f"{first} {last}"
        elif nationality in NATIONALITY_LOCALE_MAP:
            locale = NATIONALITY_LOCALE_MAP[nationality]
            fake = faker_instances[locale]
            raw = f"{fake.first_name_male()} {fake.last_name()}"
        else:
            raise ValueError(f"Unknown nationality: {nationality}")

        # Strip diacritics to ensure Latin-ASCII output
        name = _to_ascii(raw)

        if name not in used_names:
            used_names.add(name)
            return name

    # Fallback after 200 retries: append Jr.
    fallback = f"{name} Jr."
    used_names.add(fallback)
    return fallback


def pick_nationality(rng: random.Random) -> str:
    """Weighted random selection of a nationality from NATIONALITY_WEIGHTS.

    Args:
        rng: Seeded stdlib random.Random for deterministic selection.

    Returns:
        Nationality string matching keys in NATIONALITY_LOCALE_MAP or ROMANIZED_NAMES.
    """
    nationalities = list(NATIONALITY_WEIGHTS.keys())
    weights = list(NATIONALITY_WEIGHTS.values())
    return rng.choices(nationalities, weights=weights, k=1)[0]
