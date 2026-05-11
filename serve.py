"""Tiny local web UI for generating a report.

Run with `python serve.py` (or double-click start.bat). A browser tab opens to a
form; submitting it kicks off the pipeline and redirects to the generated report.
"""
from __future__ import annotations

import calendar
import threading
import traceback
import webbrowser
from pathlib import Path

from flask import Flask, redirect, render_template_string, request, send_from_directory

from main import run

app = Flask(__name__)
DOCS_DIR = Path("docs")
MONTHS = [(i, calendar.month_name[i]) for i in range(1, 13)]

FORM_HTML = """<!doctype html>
<html><head><meta charset='utf-8'><title>Trip List Preview</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
         max-width: 560px; margin: 3rem auto; padding: 0 1rem; color: #222; }
  h1 { margin-bottom: 0.3rem; }
  .sub { color: #666; margin-bottom: 2rem; }
  label { display: block; margin-bottom: 1.1rem; }
  label > span { display: block; font-weight: 600; margin-bottom: 0.3rem; }
  input, select { font-size: 1rem; padding: 0.55rem; width: 100%; box-sizing: border-box;
                  border: 1px solid #ccc; border-radius: 4px; font-family: inherit; }
  .help { color: #888; font-size: 0.85rem; margin-top: 0.25rem; }
  .help code { background: #f3f3f3; padding: 1px 4px; border-radius: 2px; }
  button { font-size: 1rem; padding: 0.7rem 1.4rem; background: #1a73e8; color: white;
           border: 0; border-radius: 4px; cursor: pointer; }
  button:hover { background: #1557b0; }
  .error { color: #b00; background: #fee; padding: 0.8rem; border-radius: 4px;
           margin-bottom: 1rem; white-space: pre-wrap; font-family: monospace;
           font-size: 0.85rem; }
  .last { color: #555; font-size: 0.9rem; margin-top: 1.5rem; }
  .last a { color: #1a73e8; }
</style></head><body>
<h1>Trip List Preview</h1>
<div class='sub'>Top 20 most-frequently-reported species for a US county / month, with audio and spectrograms.</div>
{% if error %}<div class='error'>{{ error }}</div>{% endif %}
<form method='POST' action='/generate'>
  <label><span>County code</span>
    <input name='region' value='{{ region }}' required pattern='US-[A-Z]{2}-\\d+'
           placeholder='US-CA-073' autocomplete='off'>
    <div class='help'>Format <code>US-{ST}-{NNN}</code>. Find your county's code on
      <a href='https://ebird.org/explore' target='_blank'>ebird.org/explore</a> &rarr;
      click into a county &rarr; the code is in the URL.</div>
  </label>
  <label><span>Year</span>
    <input name='year' type='number' value='{{ year }}' min='2000' max='2030' required>
  </label>
  <label><span>Month</span>
    <select name='month' required>
      {% for n, m in months %}<option value='{{ n }}'{% if n == month %} selected{% endif %}>{{ m }}</option>{% endfor %}
    </select>
  </label>
  <button type='submit'>Generate report</button>
  <div class='help' style='margin-top:0.8rem'>First run for a new county/month takes ~30 seconds while we sample eBird checklists. Cached after that.</div>
</form>
{% if has_existing %}<div class='last'>Most recent report: <a href='/report'>open last generated report</a></div>{% endif %}
</body></html>
"""


@app.route("/")
def index():
    return render_template_string(
        FORM_HTML,
        months=MONTHS,
        error=None,
        region="US-CA-073",
        year=2026,
        month=4,
        has_existing=(DOCS_DIR / "index.html").exists(),
    )


@app.route("/generate", methods=["POST"])
def generate():
    region = request.form.get("region", "").strip().upper()
    year_raw = request.form.get("year", "").strip()
    month_raw = request.form.get("month", "").strip()
    try:
        year = int(year_raw)
        month = int(month_raw)
        run(region, year, month, remote_media=True, progress=True)
    except Exception as e:
        return render_template_string(
            FORM_HTML,
            months=MONTHS,
            error=f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}",
            region=region or "US-CA-073",
            year=year_raw or 2026,
            month=int(month_raw) if month_raw.isdigit() else 4,
            has_existing=(DOCS_DIR / "index.html").exists(),
        )
    return redirect("/report")


@app.route("/report")
def report():
    return send_from_directory(DOCS_DIR.resolve(), "index.html")


def _open_browser_when_ready():
    webbrowser.open("http://localhost:5000")


if __name__ == "__main__":
    print("Starting Trip List Preview at http://localhost:5000")
    print("Press Ctrl-C in this window to stop the server.")
    threading.Timer(1.0, _open_browser_when_ready).start()
    app.run(host="127.0.0.1", port=5000, debug=False)
