# Trip List Preview
## Attribution

This tool uses data and media from the Cornell Lab of Ornithology:

- **eBird** for species occurrence frequency by region/month. eBird is a citizen science project; the underlying data is contributed by birders worldwide. https://ebird.org
- **Macaulay Library** for audio recordings and pre-rendered spectrograms. Individual recordings are © their respective recordists. Recordings are referenced by Macaulay catalog number (ML…) and embedded via Macaulay's CDN — this tool does not host or redistribute the recordings themselves. https://www.macaulaylibrary.org

Suggested citations when referencing this tool or its outputs:

> eBird. eBird: An online database of bird distribution and abundance. Cornell Lab of Ornithology, Ithaca, NY. https://www.ebird.org

> Macaulay Library. The Macaulay Library at the Cornell Lab of Ornithology. https://www.macaulaylibrary.org


## A small tool that takes a US county code and a month, queries eBird for the top 20 most-frequent species in that county/month, and outputs an HTML page with each species' name, a representative Macaulay Library audio recording, and its spectrogram.

Live demo: https://ampelion.github.io/Trip_List_Preview/ (San Diego County, April)

## Why this exists

I built this in one Claude Code session as a learning exercise for the Anthropic Fellows application. I'm a biologist. I'd never used an agentic coding tool. The application mentioned using ClaudeCode, so I added it to my vscode interface, picked a real scientific question I'd been wanting to scope, and built it.

## How it works

- eBird API v2 for species frequency by region/month (sampled-checklist approach — see notes)
- Macaulay Library CDN for audio (mp3) and pre-rendered spectrograms (JPEG), referenced directly rather than rehosted
- Static HTML output, deployed via GitHub Pages

## Session notes

A handful of forking moments shaped the final tool:

- **Frequency proxy.** The naïve approach (presence-by-day) tied all common species at 100% in a birdy county like San Diego. Resolved by sampling ~200 checklists across the month for bar-chart-style frequencies.
- **Auth wall.** The undocumented `barchartData` endpoint that powers eBird's public bar charts requires session cookies. Pivoted to the documented v2 sampling path.
- **Spectrogram source.** Claude Code surfaced a fork between Macaulay's pre-rendered spectrograms (fast, no dependencies) vs. generating custom ones (~100MB of libraries + ffmpeg). My goal was "the user hears the birds," so we used pre-rendered spectrograms plus mp3 playback.
- **Copyright.** Claude Code flagged unprompted that Macaulay recordings are © individual recordists and some licenses prohibit redistribution. We switched to direct CDN linking instead of bundling assets — sidesteps both the license issue and a 155MB repo size problem.

The agent surfacing legal concerns before an irreversible action was highlight that justified the whole exercise.

## Limitations

- Top-20 frequency is sampled from eBird's per-day 200-checklist cap. For a high-traffic county the underlying population is larger, so the sample has some hotspot bias. Unlikely to shift ranking but worth flagging.
- Audio and spectrograms load from Macaulay's CDN. If their URL scheme changes, embeds break. Caching asset IDs would harden this for long-term use.
- One representative recording per species, no filter for vocalization type (song vs. call) or quality.

## Future work

- Filter to redistributable-licensed recordings for an offline-cacheable version
- Habitat-based subset filter — toward the actual scientific question that brought me here, whether vocalization tracks habitat vs. taxonomy
- Range-map overlay per species
