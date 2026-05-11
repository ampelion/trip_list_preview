"""eBird API client.

Frequency estimation: matches eBird bar charts in spirit — for each (county, month),
we collect all checklist IDs across the month's days, sample N of them deterministically,
fetch each, and compute frequency = (# sampled checklists containing species) / N.

All API responses are cached to disk; re-runs hit no network.
"""
from __future__ import annotations

import calendar
import json
import random
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import requests

API_BASE = "https://api.ebird.org/v2"
DEFAULT_CACHE_DIR = Path("cache")


@dataclass(frozen=True)
class SpeciesFreq:
    species_code: str
    common_name: str
    scientific_name: str
    n_with: int
    n_sampled: int

    @property
    def frequency(self) -> float:
        return self.n_with / self.n_sampled if self.n_sampled else 0.0


def _cached_json(path: Path, fetch: Callable[[], object], use_cache: bool):
    if use_cache and path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    data = fetch()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return data


class EBirdClient:
    def __init__(
        self,
        api_key: str,
        session: requests.Session | None = None,
        timeout: int = 30,
        cache_dir: Path = DEFAULT_CACHE_DIR,
    ):
        if not api_key:
            raise ValueError("EBIRD_API_KEY is empty — set it in .env")
        self.api_key = api_key
        self.session = session or requests.Session()
        self.session.headers.update({"X-eBirdApiToken": api_key})
        self.timeout = timeout
        self.cache_dir = cache_dir

    def _get(self, url: str, params: dict | None = None):
        r = self.session.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def taxonomy(self, use_cache: bool = True) -> dict[str, tuple[str, str]]:
        path = self.cache_dir / "taxonomy.json"
        raw = _cached_json(
            path,
            lambda: self._get(f"{API_BASE}/ref/taxonomy/ebird", params={"fmt": "json", "cat": "species"}),
            use_cache,
        )
        return {row["speciesCode"]: (row.get("comName", ""), row.get("sciName", "")) for row in raw}

    def lists_for_day(self, region: str, year: int, month: int, day: int, max_results: int = 200, use_cache: bool = True):
        path = self.cache_dir / "lists" / region / f"{year}-{month:02d}" / f"{day:02d}.json"
        return _cached_json(
            path,
            lambda: self._get(
                f"{API_BASE}/product/lists/{region}/{year}/{month}/{day}",
                params={"maxResults": max_results},
            ),
            use_cache,
        )

    def checklist_view(self, sub_id: str, use_cache: bool = True):
        path = self.cache_dir / "checklists" / f"{sub_id}.json"
        return _cached_json(
            path,
            lambda: self._get(f"{API_BASE}/product/checklist/view/{sub_id}"),
            use_cache,
        )

    def top_species_for_month(
        self,
        region: str,
        year: int,
        month: int,
        top_n: int = 20,
        sample_size: int = 200,
        sleep_between: float = 0.1,
        seed: int | None = None,
        progress: bool = False,
        use_cache: bool = True,
    ) -> list[SpeciesFreq]:
        days_in_month = calendar.monthrange(year, month)[1]
        lists_dir = self.cache_dir / "lists" / region / f"{year}-{month:02d}"

        pool: list[str] = []
        for day in range(1, days_in_month + 1):
            was_cached = use_cache and (lists_dir / f"{day:02d}.json").exists()
            if progress:
                tag = " (cached)" if was_cached else ""
                print(f"  listing day {day:02d}/{days_in_month}{tag}...    ", end="\r", flush=True)
            day_lists = self.lists_for_day(region, year, month, day, use_cache=use_cache)
            pool.extend(item["subId"] for item in day_lists if "subId" in item)
            if not was_cached and sleep_between:
                time.sleep(sleep_between)
        if progress:
            print(" " * 60, end="\r")
            print(f"  found {len(pool)} checklists across {days_in_month} days")

        if not pool:
            return []

        rng = random.Random(seed if seed is not None else f"{region}-{year}-{month}")
        sample_n = min(sample_size, len(pool))
        sampled = rng.sample(pool, sample_n)

        ck_dir = self.cache_dir / "checklists"
        counts: Counter[str] = Counter()
        for i, sub_id in enumerate(sampled, 1):
            was_cached = use_cache and (ck_dir / f"{sub_id}.json").exists()
            if progress:
                tag = " (cached)" if was_cached else ""
                print(f"  checklist {i:>3}/{sample_n}{tag}...    ", end="\r", flush=True)
            data = self.checklist_view(sub_id, use_cache=use_cache)
            seen_codes = {o["speciesCode"] for o in data.get("obs", []) if o.get("speciesCode")}
            counts.update(seen_codes)
            if not was_cached and sleep_between:
                time.sleep(sleep_between)
        if progress:
            print(" " * 60, end="\r")

        tax = self.taxonomy(use_cache=use_cache)
        ranked = counts.most_common(top_n)
        return [
            SpeciesFreq(
                species_code=code,
                common_name=tax.get(code, ("", ""))[0],
                scientific_name=tax.get(code, ("", ""))[1],
                n_with=c,
                n_sampled=sample_n,
            )
            for code, c in ranked
        ]
