"""Macaulay Library media client.

Uses the undocumented public search endpoint at search.macaulaylibrary.org/api/v1/search
(same endpoint the public website uses; no auth required). Each asset's audio mp3 and
small spectrogram JPEG are fetched from cdn.download.ams.birds.cornell.edu.
"""
from __future__ import annotations

import json
from pathlib import Path

import requests

SEARCH_URL = "https://search.macaulaylibrary.org/api/v1/search"
ASSET_URL = "https://cdn.download.ams.birds.cornell.edu/api/v1/asset/{asset_id}/{kind}"

DEFAULT_CACHE_DIR = Path("cache") / "macaulay"


class MacaulayClient:
    def __init__(
        self,
        session: requests.Session | None = None,
        cache_dir: Path = DEFAULT_CACHE_DIR,
        timeout: int = 60,
    ):
        self.session = session or requests.Session()
        self.session.headers.setdefault("User-Agent", "trip-list-preview/0.1")
        self.cache_dir = cache_dir
        self.timeout = timeout

    def search_best_audio(self, species_code: str, use_cache: bool = True) -> dict | None:
        path = self.cache_dir / "search" / f"{species_code}.json"
        if use_cache and path.exists():
            raw = path.read_text(encoding="utf-8")
            return json.loads(raw) if raw.strip() != "null" else None
        params = {
            "taxonCode": species_code,
            "mediaType": "audio",
            "sort": "rating_rank_desc",
            "count": 1,
        }
        r = self.session.get(SEARCH_URL, params=params, timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        content = data.get("results", {}).get("content", [])
        result = content[0] if content else None
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result) if result else "null", encoding="utf-8")
        return result

    def download_asset(self, asset_id: str, kind: str, dest: Path) -> bool:
        """Download an asset to `dest`. Returns True if a network fetch happened."""
        if dest.exists() and dest.stat().st_size > 0:
            return False
        url = ASSET_URL.format(asset_id=asset_id, kind=kind)
        with self.session.get(url, stream=True, timeout=self.timeout) as r:
            r.raise_for_status()
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("wb") as f:
                for chunk in r.iter_content(chunk_size=64 * 1024):
                    if chunk:
                        f.write(chunk)
        return True
