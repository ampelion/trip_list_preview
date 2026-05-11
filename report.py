"""HTML report generator."""
from __future__ import annotations

import calendar
import html
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SpeciesEntry:
    rank: int
    species_code: str
    common_name: str
    scientific_name: str
    frequency: float
    n_with: int
    n_sampled: int
    asset_id: str | None
    audio_rel: str | None
    spectrogram_rel: str | None
    recordist: str | None
    asset_url: str | None


_PAGE_CSS = """
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
       max-width: 1100px; margin: 1.5rem auto; padding: 0 1rem; color: #222; }
h1 { margin-bottom: 0.2rem; }
.subtitle { color: #666; margin-bottom: 2rem; }
.species { display: grid; grid-template-columns: 60px 1fr; gap: 1rem;
           padding: 1rem 0; border-bottom: 1px solid #eee; }
.rank { font-size: 1.5rem; color: #999; text-align: right; padding-top: 0.25rem; }
.name { font-size: 1.15rem; font-weight: 600; }
.name a { color: #1a73e8; text-decoration: none; }
.sci  { font-style: italic; color: #555; font-size: 0.95rem; }
.meta { color: #777; font-size: 0.85rem; margin: 0.2rem 0 0.5rem 0; }
.spec img { display: block; max-width: 100%; height: auto; border-radius: 4px;
            border: 1px solid #ddd; }
audio { width: 100%; margin-top: 0.5rem; }
.no-media { color: #b00; font-size: 0.9rem; }
.attrib { color: #888; font-size: 0.8rem; margin-top: 0.3rem; }
.attrib a { color: #888; }
"""


def render(
    region: str,
    year: int,
    month: int,
    entries: list[SpeciesEntry],
    out_path: Path,
) -> None:
    month_name = calendar.month_name[month]
    n_sampled = entries[0].n_sampled if entries else 0

    parts: list[str] = []
    parts.append("<!doctype html><html><head><meta charset='utf-8'>")
    parts.append(f"<title>Top species — {html.escape(region)} {month_name} {year}</title>")
    parts.append(f"<style>{_PAGE_CSS}</style></head><body>")
    parts.append(f"<h1>Top species — {html.escape(region)}, {month_name} {year}</h1>")
    parts.append(
        f"<div class='subtitle'>Top {len(entries)} species by frequency across "
        f"{n_sampled} sampled eBird checklists. Audio &amp; spectrograms © "
        "<a href='https://www.macaulaylibrary.org/'>Macaulay Library</a>, Cornell Lab of Ornithology.</div>"
    )

    for e in entries:
        parts.append("<div class='species'>")
        parts.append(f"<div class='rank'>{e.rank}</div>")
        parts.append("<div>")
        ebird_url = f"https://ebird.org/species/{e.species_code}"
        parts.append(
            f"<div class='name'><a href='{ebird_url}'>{html.escape(e.common_name)}</a></div>"
        )
        parts.append(f"<div class='sci'>{html.escape(e.scientific_name)}</div>")
        parts.append(
            f"<div class='meta'>{e.frequency:.0%} of checklists "
            f"({e.n_with}/{e.n_sampled}) · <code>{html.escape(e.species_code)}</code></div>"
        )
        if e.spectrogram_rel:
            parts.append(f"<div class='spec'><img src='{html.escape(e.spectrogram_rel)}' alt='spectrogram'></div>")
        if e.audio_rel:
            parts.append(f"<audio controls preload='none' src='{html.escape(e.audio_rel)}'></audio>")
        if not e.audio_rel and not e.spectrogram_rel:
            parts.append("<div class='no-media'>No Macaulay audio found for this species.</div>")
        if e.asset_id and e.asset_url:
            who = html.escape(e.recordist or "Unknown recordist")
            parts.append(
                f"<div class='attrib'>ML{html.escape(e.asset_id)} · {who} · "
                f"<a href='{e.asset_url}'>view on Macaulay</a></div>"
            )
        parts.append("</div></div>")

    parts.append("</body></html>")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(parts), encoding="utf-8")
