#!/usr/bin/env python3
"""Generate local SVG analytics from public GitHub repository metadata."""

import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
from urllib.request import Request, urlopen

USERNAME = "Euvouserdoutor"
OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "analytics"


def public_repositories():
    token = os.environ.get("GITHUB_TOKEN", "")
    headers = {
        "User-Agent": "profile-public-analytics/1.0",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    repos = []
    page = 1
    while True:
        endpoint = f"https://api.github.com/users/{USERNAME}/repos?type=owner&per_page=100&page={page}"
        with urlopen(Request(endpoint, headers=headers), timeout=25) as response:
            batch = json.load(response)
        if not isinstance(batch, list):
            raise ValueError("GitHub did not return a repository list")
        repos.extend(
            r for r in batch
            if r.get("owner", {}).get("login", "").lower() == USERNAME.lower()
            and r.get("private") is False
        )
        if len(batch) < 100:
            break
        page += 1
        if page > 20:
            raise ValueError("Unexpected pagination length")
    return repos


def svg_frame(title, subtitle, inner, width, height, description):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">'
        f'<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>'
        f'<rect x="1" y="1" width="{width-2}" height="{height-2}" rx="8" '
        'fill="#0d1117" stroke="#30363d"/>'
        f'<text x="24" y="31" fill="#e6edf3" font-family="Arial,Helvetica,sans-serif" '
        f'font-size="18" font-weight="700">{escape(title)}</text>'
        f'<text x="{width-25}" y="29" text-anchor="end" fill="#8b949e" '
        f'font-family="Arial,Helvetica,sans-serif" font-size="11">{escape(subtitle)}</text>'
        f'<path d="M24 47H{width-24}" stroke="#30363d"/>' + inner + '</svg>\n'
    )


def make_cards(repos, today=None):
    now = today or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=30)
    total = len(repos)
    originals = sum(not r.get("fork", False) for r in repos)
    stars = sum(int(r.get("stargazers_count") or 0) for r in repos)
    active = 0
    for r in repos:
        pushed = r.get("pushed_at")
        if pushed:
            try:
                active += datetime.fromisoformat(pushed.replace("Z", "+00:00")) >= cutoff
            except (ValueError, TypeError):
                continue
    stamp = now.strftime("%Y-%m-%d")
    info = [
        (total, "Public repositories", 28),
        (originals, "Original repositories", 218),
        (stars, "Repository stars", 406),
        (active, "Updated in 30 days", 576),
    ]
    stats_rows = ''.join(
        f'<text x="{x}" y="99" fill="#58a6ff" font-family="Arial,Helvetica,sans-serif" '
        f'font-size="35" font-weight="700">{value}</text>'
        f'<text x="{x}" y="128" fill="#b1bac4" font-family="Arial,Helvetica,sans-serif" '
        f'font-size="13">{escape(label)}</text>'
        for value, label, x in info
    )
    stats = svg_frame(
        "GitHub Analytics", f"Public repos · {stamp}", stats_rows, 760, 164,
        f"{total} public repositories; {originals} originals; {stars} stars; "
        f"{active} repos updated in the last 30 days as of {stamp}.",
    )

    langs = Counter(r.get("language") for r in repos if r.get("language"))
    top = langs.most_common(5)
    colors = {
        "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Python": "#3572a5",
        "Go": "#00ADD8", "CSS": "#563d7c",
    }
    maximum = max((v for _, v in top), default=1)
    lang_rows = ''
    for i, (language, count) in enumerate(top):
        y = 87 + 29 * i
        width = max(12, round(423 * count / maximum))
        color = colors.get(language, "#58a6ff")
        lang_rows += (
            f'<text x="27" y="{y+1}" fill="#c9d1d9" font-family="Arial,Helvetica,sans-serif" '
            f'font-size="13">{escape(language)}</text>'
            f'<rect x="142" y="{y-11}" width="423" height="13" rx="4" fill="#21262d"/>'
            f'<rect x="142" y="{y-11}" width="{width}" height="13" rx="4" fill="{color}"/>'
            f'<text x="578" y="{y+1}" fill="#8b949e" font-family="Arial,Helvetica,sans-serif" '
            f'font-size="12">{count} {"repo" if count == 1 else "repos"}</text>'
        )
    lang_rows += (
        '<text x="24" y="236" fill="#8b949e" font-family="Arial,Helvetica,sans-serif" '
        'font-size="10.5">Repositories without a detected language are omitted. '
        'Based on GitHub API metadata.</text>'
    )
    languages = svg_frame(
        "Primary Languages", "By public repository count", lang_rows, 760, 248,
        "; ".join(f"{lang}: {count} repos" for lang, count in top) or "No language metadata detected.",
    )
    return {"public-stats.svg": stats, "primary-languages.svg": languages}


def main():
    repos = public_repositories()
    cards = make_cards(repos)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name, card in cards.items():
        (OUTPUT / name).write_text(card, encoding="utf-8")
    print(f"Updated {len(cards)} public GitHub SVG cards from {len(repos)} public repositories")


if __name__ == "__main__":
    main()
