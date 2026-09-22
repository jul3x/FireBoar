"""Exercise GIF lookup in the bundled ExerciseDB catalog, with Polish name support.

ExerciseDB only has English names, so Polish gym vocabulary is translated here with a
small dictionary (prefix-matched stems handle Polish inflection: sztanga/sztangi/sztangą).
Only when that finds nothing the name goes through a free online translator.
"""
from __future__ import annotations
import re
import json
import difflib
from pathlib import Path
from urllib.parse import quote
import httpx

CATALOG_PATH = Path(__file__).parent / "data" / "exercisedb.json"
TRANSLATE_URL = "https://api.mymemory.translated.net/get"
# static.exercisedb.dev sends no CORS headers and Flutter web loads images via XHR, so on web
# the GIFs would be blocked. wsrv.nl re-serves them with CORS allowed (n=-1 keeps all frames).
IMAGE_PROXY_URL = "https://wsrv.nl/?n=-1&url="
# Required by the free ExerciseDB V1 dataset terms (see scripts/fetch_exercisedb.py)
ATTRIBUTION = "GIF-y ćwiczeń: ExerciseDB by AscendAPI (ascendapi.com)"

_PL_CHARS = str.maketrans("ąćęłńóśźż", "acelnoszz")

# Matched first, on normalized text (no diacritics).
PL_PHRASES = {
    "martwy ciag rumunski": "romanian deadlift",
    "martwy ciag": "deadlift",
    "wyciskanie francuskie": "lying triceps extension",
    "sztanga lamana": "ez barbell",
    "sztangi lamanej": "ez barbell",
    "sztanga ez": "ez barbell",
    "przysiad bulgarski": "split squat",
    "wyciskanie zolnierskie": "military press",
    "nad glowe": "overhead",
    "nad glowa": "overhead",
    "wypychanie nog": "leg press",
    "dzien dobry": "good morning",
    "wspiecia na palce": "calf raise",
    "sciaganie drazka": "pulldown",
    "sciaganie": "pulldown",
    "hip thrust": "hip thrust",
}

# Single-token prefixes, longest prefix wins. Empty value = ignore the word.
PL_STEMS = {
    "wycisk": "press",
    "sztang": "barbell",
    "hantl": "dumbbell",
    "hantel": "dumbbell",
    "sztangiel": "dumbbell",
    "kettl": "kettlebell",
    "odwazn": "kettlebell",
    "lawk": "bench",
    "lawc": "bench",
    "lawec": "bench",
    "skos": "incline",
    "ujemn": "decline",
    "przysiad": "squat",
    "wykrok": "lunge",
    "zakrok": "reverse lunge",
    "podciag": "pull up",
    "drazk": "bar",
    "drazek": "bar",
    "wioslow": "row",
    "uginan": "curl",
    "prostowan": "extension",
    "rozpiet": "fly",
    "motyl": "fly",
    "pompk": "push up",
    "brzuszk": "crunch",
    "spiecia": "crunch",
    "desk": "plank",
    "mostek": "bridge",
    "wyciag": "cable",
    "link": "cable",
    "maszyn": "lever",
    "suwnic": "sled leg press",
    "lydk": "calf",
    "wspiec": "calf raise",
    "porecz": "dip",
    "dipy": "dip",
    "szrug": "shrug",
    "wymach": "swing",
    "gum": "band",
    "siedz": "seated",
    "stoj": "standing",
    "lez": "lying",
    "opad": "bent over",
    "pochyl": "bent over",
    "jednorac": "one arm",
    "jednonoz": "single leg",
    "mlotk": "hammer dumbbell",  # hammer curls are done with dumbbells
    "modlitewnik": "preacher",
    "podchwyt": "reverse grip",
    "wask": "close grip",
    "szerok": "wide grip",
    "unoszen": "raise",
    "wznos": "raise",
    "bokiem": "lateral",
    "przodem": "front",
    "odwrot": "reverse",
    "francusk": "french press",
    "rumunsk": "romanian",
    "bulgarsk": "split squat",
    "zolniersk": "military press",
    "nog": "leg",
    "klat": "chest",
    "bark": "shoulder",
    "plec": "back",
    "bicep": "biceps",
    "tricep": "triceps",
    "przedrami": "wrist",
    "nadgarst": "wrist",
    "ramion": "",
    "ramie": "",
    "ramienia": "",
    "reka": "",
    "reki": "",
    "na": "",
    "ze": "",
    "do": "",
    "za": "",
    "przy": "",
    "pod": "",
    "nad": "",
    "po": "",
    "od": "",
}

EQUIPMENT = {"barbell", "dumbbell", "cable", "lever", "band", "kettlebell", "smith", "sled", "ez", "machine", "bodyweight"}

STOPWORDS = {"z", "w", "i", "o", "na", "ze", "do", "za", "we", "the", "with", "on", "and", "to", "a"}

_catalog: list[dict] | None = None
_vocab: set[str] | None = None


def normalize(s: str) -> str:
    s = s.lower().translate(_PL_CHARS)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return s.strip()


def _singular(token: str) -> str:
    # ropes/rope, dips/dip, biceps/bicep - but keep press, cross
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _tokens(s: str) -> list[str]:
    return [_singular(t) for t in normalize(s).split() if t not in STOPWORDS]


def load_catalog() -> list[dict]:
    global _catalog, _vocab
    if _catalog is None:
        raw = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        _catalog = [dict(e, tokens=set(_tokens(e["name"]))) for e in raw]
        _vocab = set().union(*(e["tokens"] for e in _catalog))
    return _catalog


def _vocab_word(token: str) -> str | None:
    load_catalog()
    token = _singular(token)
    if token in _vocab:
        return token
    if len(token) < 4:
        return None
    close = difflib.get_close_matches(token, _vocab, n=1, cutoff=0.8)
    return close[0] if close else None


def translate_query(name: str) -> list[str]:
    """Polish (or English) exercise name -> English tokens from the catalog vocabulary."""
    text = f" {normalize(name)} "
    words: list[str] = []
    for phrase, english in PL_PHRASES.items():
        if f" {phrase} " in text:
            words.extend(_singular(w) for w in english.split())
            text = text.replace(f" {phrase} ", " ")

    stems = sorted(PL_STEMS, key=len, reverse=True)
    for token in text.split():
        if token in STOPWORDS:
            continue
        stem = next((s for s in stems if token.startswith(s)), None)
        if stem is not None:
            words.extend(_singular(w) for w in PL_STEMS[stem].split())
            continue
        known = _vocab_word(token)
        if known:
            words.append(known)

    return list(dict.fromkeys(words))


def search_tokens(words: list[str], limit: int = 8) -> list[dict]:
    if not words:
        return []
    # "Martwy ciąg" says nothing about equipment - the gym default is the barbell version
    prefer_barbell = not EQUIPMENT & set(words)
    scored = []
    for entry in load_catalog():
        matched = sum(1 for w in words if w in entry["tokens"])
        if not matched:
            continue
        extra = len(entry["tokens"]) - matched
        # each matched word counts 10x more than an unrelated extra word in the name
        score = 10 * matched - extra
        if prefer_barbell and "barbell" in entry["tokens"]:
            score += 2  # outweighs its own extra-word penalty plus one more
        scored.append((score, entry))
    scored.sort(key=lambda x: (-x[0], len(x[1]["name"]), x[1]["name"]))
    return [{"id": e["id"], "name": e["name"], "gif": e["gif"]} for _, e in scored[:limit]]


def display_url(gif_url: str) -> str:
    """Stored URLs stay the original ExerciseDB ones - the proxy is applied only for display."""
    if not gif_url:
        return ""
    return IMAGE_PROXY_URL + quote(gif_url, safe="")


def search(name: str, limit: int = 8) -> list[dict]:
    return search_tokens(translate_query(name), limit)


async def remote_translate(name: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(TRANSLATE_URL, params={"q": name, "langpair": "pl|en"})
            return r.json()["responseData"]["translatedText"] or ""
    except Exception as e:
        print(f"Translation failed: {e}")
        return ""


async def find_gifs(name: str, limit: int = 8) -> list[dict]:
    results = search(name, limit)
    if results or not name.strip():
        return results
    translated = await remote_translate(name)
    return search(translated, limit) if translated else []
