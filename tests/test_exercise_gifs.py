"""
Unit tests for exercise GIF lookup in fireboar.exercise_gifs.
Runs against the bundled ExerciseDB catalog (fireboar/data/exercisedb.json).
"""
import pytest
from fireboar.exercise_gifs import normalize, translate_query, search, load_catalog, display_url


def top(name: str) -> str:
    results = search(name, limit=1)
    assert results, f"no results for {name!r}"
    return results[0]["name"]


def test_catalog_is_bundled():
    catalog = load_catalog()
    assert len(catalog) > 1000
    assert all(e["gif"].startswith("https://") for e in catalog)


def test_normalize_strips_polish_chars_and_punctuation():
    assert normalize("Wyciskanie SZTANGI na ławce, skośnej!") == "wyciskanie sztangi na lawce skosnej"
    assert normalize("Martwy ciąg / żółw") == "martwy ciag zolw"


def test_translate_query_handles_inflection():
    assert translate_query("sztanga") == translate_query("sztangi") == translate_query("sztangą") == ["barbell"]


def test_translate_query_phrase_before_stems():
    assert translate_query("Martwy ciąg rumuński") == ["romanian", "deadlift"]


@pytest.mark.parametrize("name, expected", [
    ("Wyciskanie sztangi na ławce", "barbell bench press"),
    ("Wyciskanie sztangi na ławce skośnej", "barbell incline bench press"),
    ("Martwy ciąg", "barbell deadlift"),
    ("Martwy ciąg rumuński", "barbell romanian deadlift"),
    ("Podciąganie na drążku", "pull-up"),
    ("Pompki", "push-up"),
    ("Wypychanie nóg na suwnicy", "sled 45в° leg press"),
    ("Prostowanie nóg na maszynie", "lever leg extension"),
    ("Uginanie młotkowe", "dumbbell hammer curl"),
])
def test_polish_names_find_expected_exercise(name, expected):
    assert top(name) == expected


@pytest.mark.parametrize("name, words", [
    ("Przysiad ze sztangą", {"barbell", "squat"}),
    ("Wiosłowanie hantlem", {"dumbbell", "row"}),
    ("Wiosłowanie sztangą w opadzie", {"barbell", "bent", "over", "row"}),
    ("Wznosy bokiem hantlami", {"dumbbell", "lateral", "raise"}),
    ("Ściąganie drążka wyciągu", {"cable", "pulldown"}),
])
def test_polish_names_match_all_key_words(name, words):
    assert words <= set(normalize(top(name)).split())


def test_english_names_pass_through():
    assert translate_query("Barbell bench press") == ["barbell", "bench", "press"]
    assert top("Barbell bench press") == "barbell bench press"


def test_typo_tolerance():
    assert top("barbel bench pres") == "barbell bench press"


def test_plurals_match_singular_names():
    # the online translator fallback answers e.g. "Jump Ropes"
    assert top("Jump Ropes") == "jump rope"


def test_equipment_given_disables_barbell_default():
    assert top("Martwy ciąg z hantlami").startswith("dumbbell")


def test_unknown_name_returns_nothing():
    assert search("asdfgh qwerty") == []
    assert search("") == []


def test_display_url_goes_through_cors_proxy():
    url = display_url("https://static.exercisedb.dev/media/RRWFUcw.gif")
    assert url.startswith("https://wsrv.nl/")
    assert "static.exercisedb.dev%2Fmedia%2FRRWFUcw.gif" in url
    assert display_url("") == ""
