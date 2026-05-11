"""CLI entry point and reusable pipeline function."""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from ebird import EBirdClient
from macaulay import MacaulayClient
from report import SpeciesEntry, render


def run(
    region: str,
    year: int,
    month: int,
    *,
    api_key: str | None = None,
    top: int = 20,
    sample_size: int = 200,
    output_dir: str = "docs",
    remote_media: bool = False,
    skip_media: bool = False,
    use_cache: bool = True,
    progress: bool = False,
) -> Path:
    """Run the full pipeline; return the path to the generated HTML."""
    if api_key is None:
        load_dotenv()
        api_key = os.environ.get("EBIRD_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("EBIRD_API_KEY not set. Copy .env.example to .env and fill it in.")

    out_dir = Path(output_dir)
    audio_dir = out_dir / "audio"
    spec_dir = out_dir / "spectrograms"

    ebird = EBirdClient(api_key)
    species = ebird.top_species_for_month(
        region, year, month,
        top_n=top, sample_size=sample_size,
        progress=progress, use_cache=use_cache,
    )

    entries: list[SpeciesEntry] = []
    if species and not skip_media:
        ml = MacaulayClient()
        if progress:
            print(f"\nFetching Macaulay media for {len(species)} species...")
        for i, s in enumerate(species, 1):
            if progress:
                print(f"  [{i:>2}/{len(species)}] {s.common_name:<32}", end="", flush=True)
            asset = ml.search_best_audio(s.species_code, use_cache=use_cache)
            asset_id: str | None = None
            audio_rel: str | None = None
            spec_rel: str | None = None
            recordist: str | None = None
            asset_url: str | None = None

            if asset:
                asset_id = str(asset.get("assetId") or asset.get("catalogId") or "").strip() or None
                recordist = asset.get("userDisplayName")
                if asset_id:
                    asset_url = f"https://macaulaylibrary.org/asset/{asset_id}"
                    if remote_media:
                        audio_rel = f"https://cdn.download.ams.birds.cornell.edu/api/v1/asset/{asset_id}/audio"
                        spec_rel = f"https://cdn.download.ams.birds.cornell.edu/api/v1/asset/{asset_id}/spectrogram_small"
                        if progress:
                            print(f" ML{asset_id} (remote)")
                    else:
                        try:
                            ml.download_asset(asset_id, "audio", audio_dir / f"{asset_id}.mp3")
                            ml.download_asset(asset_id, "spectrogram_small", spec_dir / f"{asset_id}.jpg")
                            audio_rel = f"audio/{asset_id}.mp3"
                            spec_rel = f"spectrograms/{asset_id}.jpg"
                            if progress:
                                print(f" ML{asset_id}")
                        except Exception as e:
                            if progress:
                                print(f" ERROR: {e}")
                            audio_rel = spec_rel = None
                elif progress:
                    print(" no asset id?")
            elif progress:
                print(" no audio found")

            entries.append(SpeciesEntry(
                rank=i, species_code=s.species_code, common_name=s.common_name,
                scientific_name=s.scientific_name, frequency=s.frequency,
                n_with=s.n_with, n_sampled=s.n_sampled,
                asset_id=asset_id, audio_rel=audio_rel, spectrogram_rel=spec_rel,
                recordist=recordist, asset_url=asset_url,
            ))
            if asset_id and not remote_media:
                time.sleep(0.2)
    elif species and skip_media:
        for i, s in enumerate(species, 1):
            entries.append(SpeciesEntry(
                rank=i, species_code=s.species_code, common_name=s.common_name,
                scientific_name=s.scientific_name, frequency=s.frequency,
                n_with=s.n_with, n_sampled=s.n_sampled,
                asset_id=None, audio_rel=None, spectrogram_rel=None,
                recordist=None, asset_url=None,
            ))

    html_path = out_dir / "index.html"
    render(region, year, month, entries, html_path)
    return html_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Top species + audio for a US county/month")
    parser.add_argument("region", help="eBird region code, e.g. US-CA-073")
    parser.add_argument("year", type=int)
    parser.add_argument("month", type=int, help="1-12")
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--sample-size", type=int, default=200)
    parser.add_argument("--output-dir", default="docs")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--skip-media", action="store_true")
    parser.add_argument("--remote-media", action="store_true",
                        help="reference Macaulay CDN URLs in the HTML instead of downloading mp3/jpg locally")
    args = parser.parse_args(argv)

    try:
        html_path = run(
            args.region, args.year, args.month,
            top=args.top, sample_size=args.sample_size,
            output_dir=args.output_dir, remote_media=args.remote_media,
            skip_media=args.skip_media, use_cache=not args.no_cache,
            progress=True,
        )
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    print(f"\nWrote {html_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
