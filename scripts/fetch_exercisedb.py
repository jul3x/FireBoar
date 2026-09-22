"""Download the ExerciseDB catalog (name + GIF) into fireboar/data/exercisedb.json.

Run by hand when the catalog should be refreshed:
    python scripts/fetch_exercisedb.py
The app searches this bundled file locally - the API pages by 25 and its own search
ranks poorly, so doing it at runtime would be slow and flaky.

Terms of the free V1 dataset (https://oss.exercisedb.dev/swagger, "Usage Restrictions"):
non-commercial use only, credit to AscendAPI (https://ascendapi.com) is required - see
ATTRIBUTION in fireboar/exercise_gifs.py. Nothing there allows re-hosting the GIFs, so the
app keeps loading them from static.exercisedb.dev; mirroring them needs a paid licence.
"""
import json
import time
from pathlib import Path
import httpx

API = "https://oss.exercisedb.dev/api/v1/exercises"
OUT = Path(__file__).resolve().parent.parent / "fireboar" / "data" / "exercisedb.json"


def fetch_page(client: httpx.Client, cursor: str | None) -> dict:
    params = {"limit": 25}
    if cursor:
        params["after"] = cursor
    for attempt in range(5):
        try:
            r = client.get(API, params=params, timeout=20)
            r.raise_for_status()
            return r.json()
        except (httpx.HTTPError, ValueError) as e:
            print(f"retry {attempt + 1}/5 ({e})")
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("ExerciseDB not responding")


def main():
    exercises = {}
    cursor = None
    with httpx.Client() as client:
        while True:
            page = fetch_page(client, cursor)
            for ex in page["data"]:
                exercises[ex["exerciseId"]] = {"id": ex["exerciseId"], "name": ex["name"], "gif": ex["gifUrl"]}
            meta = page["meta"]
            print(f"{len(exercises)}/{meta['total']}")
            if not meta.get("hasNextPage"):
                break
            cursor = meta["nextCursor"]
            time.sleep(0.3)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    data = sorted(exercises.values(), key=lambda e: e["name"])
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    print(f"Saved {len(data)} exercises to {OUT}")


if __name__ == "__main__":
    main()
