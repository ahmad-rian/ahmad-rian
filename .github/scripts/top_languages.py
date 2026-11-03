"""Render a Top Languages SVG from every owned repo, private ones included.

The summary-cards action only reads public repos, which hides languages that
live mostly in private work (e.g. Go). Needs a token with `repo` scope in
GITHUB_TOKEN.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from html import escape

API = "https://api.github.com"
OUTPUT = "assets/top-languages.svg"
TOP_N = 6
EXCLUDED = {
    "HTML", "CSS", "SCSS", "Less", "Blade", "Shell", "PowerShell", "Makefile",
    "Batchfile", "Dockerfile", "Procfile", "FreeMarker", "PLpgSQL", "CMake",
    "Jupyter Notebook", "Hack",
}
COLORS = {
    "TypeScript": "#3178c6", "PHP": "#4F5D95", "JavaScript": "#f1e05a",
    "Go": "#00ADD8", "Python": "#3572A5", "Dart": "#00B4AB", "Rust": "#dea584",
    "C++": "#f34b7d", "Vue": "#41b883", "Swift": "#F05138", "Ruby": "#701516",
}
FALLBACK_COLOR = "#8b949e"
# tokyonight, matching the other cards
BG, TITLE, TEXT, MUTED = "#1a1b27", "#70a5fd", "#38bdae", "#a9b1d6"


def fetch_json(url, token):
    request = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    })
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def owned_repos(token):
    page = 1
    while True:
        batch = fetch_json(
            f"{API}/user/repos?affiliation=owner&per_page=100&page={page}", token)
        if not batch:
            return
        yield from (repo for repo in batch if not repo["fork"])
        page += 1


def language_totals(token):
    totals = {}
    for repo in owned_repos(token):
        for name, size in fetch_json(repo["languages_url"], token).items():
            if name not in EXCLUDED:
                totals[name] = totals.get(name, 0) + size
    return totals


def render(totals):
    grand_total = sum(totals.values())
    ranked = sorted(totals.items(), key=lambda item: -item[1])[:TOP_N]
    shares = [(name, size / grand_total * 100) for name, size in ranked]

    bar_x, bar_y, bar_width = 25, 62, 417
    segments, offset = [], 0.0
    for name, share in shares:
        width = bar_width * share / 100
        color = COLORS.get(name, FALLBACK_COLOR)
        segments.append(f'<rect x="{bar_x + offset:.2f}" y="{bar_y}" '
                        f'width="{width:.2f}" height="10" fill="{color}"/>')
        offset += width

    legend = []
    for index, (name, share) in enumerate(shares):
        x = 25 + (index % 2) * 215
        y = 100 + (index // 2) * 28
        color = COLORS.get(name, FALLBACK_COLOR)
        legend.append(
            f'<circle cx="{x + 5}" cy="{y - 4}" r="5" fill="{color}"/>'
            f'<text x="{x + 18}" y="{y}" class="lang">{escape(name)}</text>'
            f'<text x="{x + 190}" y="{y}" class="pct" text-anchor="end">{share:.1f}%</text>')

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="467" height="195" viewBox="0 0 467 195">
<style>
.title {{ font: 600 20px 'Segoe UI', Ubuntu, sans-serif; fill: {TITLE}; }}
.lang {{ font: 400 14px 'Segoe UI', Ubuntu, sans-serif; fill: {TEXT}; }}
.pct {{ font: 400 13px 'Segoe UI', Ubuntu, sans-serif; fill: {MUTED}; }}
.note {{ font: 400 11px 'Segoe UI', Ubuntu, sans-serif; fill: {MUTED}; }}
</style>
<rect width="467" height="195" rx="6" fill="{BG}"/>
<text x="25" y="40" class="title">Top Languages</text>
<text x="442" y="40" class="note" text-anchor="end">all repos, incl. private</text>
<clipPath id="bar"><rect x="{bar_x}" y="{bar_y}" width="{bar_width}" height="10" rx="5"/></clipPath>
<g clip-path="url(#bar)">{''.join(segments)}</g>
{''.join(legend)}
</svg>
'''


def main():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("GITHUB_TOKEN is not set")
    try:
        totals = language_totals(token)
    except urllib.error.HTTPError as error:
        sys.exit(f"GitHub API {error.code} for {error.url}: needs a personal "
                 "access token with `repo` scope in SUMMARY_GITHUB_TOKEN")
    if not totals:
        sys.exit("No language data returned; check the token's repo scope")
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as handle:
        handle.write(render(totals))
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
