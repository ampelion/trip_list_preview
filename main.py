"""CLI entry point: query eBird, fetch Macaulay media, render HTML report."""
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Top species + audio for a US county/month")
    parser.add_argument("region", help="eBird region code, e.g. US-CA-073")
    parser.add_argument("year", type=int)
    parser.add_argument("month", type=int, help="1-12")
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--sample-size", type=int, default=200)
    parser.add_argument("--output-dir", default="docs")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--skip-media", action="store_true", help="skip Macaulay downloads, just produce table")
    parser.add_argument("--remote-media", action="store_true",
                        help="reference Macaulay CDN URLs in the HTML instead of downloading mp3/jpg locally")
    args = parser.parse_args(argv)

    load_dotenv()
    api_key = os.environ.get("EBIRD_API_KEY", "").strip()
    if not api_key:
        print("ERROR: EBIRD_API_KEY not set. Copy .env.example to .env and fill it in.", file=sys.stderr)
        return 2

    out_dir = Path(args.output_dir)
    audio_dir = out_dir / "audio"
    spec_dir = out_dir / "spectrograms"

    ebird = EBirdClient(api_key)
    print(f"Querying eBird for {args.region} {args.year}-{args.month:02d} (sample={args.sample_size})...")
    species = ebird.top_species_for_month(
        args.region,
        args.year,
        args.month,
        top_n=args.top,
        sample_size=args.sample_size,
        progress=True,
        use_cache=not args.no_cache,
    )
    if not species:
        print("No species found.")
        return 0

    entries: list[SpeciesEntry] = []
    if args.skip_media:
        for i, s in enumerate(species, 1):
            entries.append(SpeciesEntry(
                rank=i, species_code=s.species_code, common_name=s.common_name,
                scientific_name=s.scientific_name, frequency=s.frequency,
                n_with=s.n_with, n_sampled=s.n_sampled,
                asset_id=None, audio_rel=None, spectrogram_rel=None,
                recordist=None, asset_url=None,
            ))
    else:
        ml = MacaulayClient()
        print(f"\nFetching Macaulay media for {len(species)} species...")
        for i, s in enumerate(species, 1):
            print(f"  [{i:>2}/{len(species)}] {s.common_name:<32}", end="", flush=True)
            asset = ml.search_best_audio(s.species_code, use_cache=not args.no_cache)
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
                    if args.remote_media:
                        audio_rel = f"https://cdn.download.ams.birds.cornell.edu/api/v1/asset/{asset_id}/audio"
                        spec_rel = f"https://cdn.download.ams.birds.cornell.edu/api/v1/asset/{asset_id}/spectrogram_small"
                        print(f" ML{asset_id} (remote)")
                    else:
                        audio_path = audio_dir / f"{asset_id}.mp3"
                        spec_path = spec_dir / f"{asset_id}.jpg"
                        try:
                            fetched_a = ml.download_asset(asset_id, "audio", audio_path)
                            fetched_s = ml.download_asset(asset_id, "spectrogram_small", spec_path)
                            audio_rel = f"audio/{asset_id}.mp3"
                            spec_rel = f"spectrograms/{asset_id}.jpg"
                            tag = []
                            if fetched_a: tag.append("audio")
                            if fetched_s: tag.append("spec")
                            if not tag: tag.append("cached")
                            print(f" ML{asset_id} ({', '.join(tag)})")
                        except Exception as e:
                            print(f" ERROR: {e}")
                            audio_rel = spec_rel = None
                else:
                    print(" no asset id?")
            else:
                print(" no audio found")

            entries.append(SpeciesEntry(
                rank=i, species_code=s.species_code, common_name=s.common_name,
                scientific_name=s.scientific_name, frequency=s.frequency,
                n_with=s.n_with, n_sampled=s.n_sampled,
                asset_id=asset_id, audio_rel=audio_rel, spectrogram_rel=spec_rel,
                recordist=recordist, asset_url=asset_url,
            ))
            if asset_id and (audio_rel or spec_rel):
                time.sleep(0.2)

    html_path = out_dir / "index.html"
    render(args.region, args.year, args.month, entries, html_path)
    print(f"\nWrote {html_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
