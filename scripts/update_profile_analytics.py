#!/usr/bin/env python3
"""Render GitHub profile analytics from public GitHub API data only."""

import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

USERNAME = "Euvouserdoutor"
OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "analytics"


def api_json(url):
    token = os.environ.get("GITHUB_TOKEN", "")
    headers = {
        "User-Agent": "euvouserdoutor-profile-analytics/2.0",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urlopen(Request(url, headers=headers), timeout=30) as response:
        return json.load(response)


def public_repositories():
    repos = []
    for page in range(1, 22):
        url = f"https://api.github.com/users/{USERNAME}/repos?type=owner&per_page=100&page={page}"
        batch = api_json(url)
        if not isinstance(batch, list):
            raise ValueError("GitHub repository response must be a list")
        repos.extend(
            item for item in batch
            if item.get("owner", {}).get("login", "").lower() == USERNAME.lower()
            and item.get("private") is False
        )
        if len(batch) < 100:
            return repos
    raise ValueError("Repository pagination exceeded the supported limit")


def search_total(query):
    """Read public GitHub search total without downloading item descriptions."""
    try:
        result = api_json(
            "https://api.github.com/search/issues?q=" + quote(query, safe="") + "&per_page=1"
        )
    except (HTTPError, URLError, TimeoutError) as exc:
        print(f"GitHub search unavailable for '{query}': {type(exc).__name__}")
        return None
    count = result.get("total_count")
    if result.get("incomplete_results") is True or not isinstance(count, int):
        return None
    return count


def frame(title, subtitle, body, description):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="520" height="312" '
        'viewBox="0 0 520 312" role="img" aria-labelledby="title desc">'
        f'<title id="title">{escape(title)}</title>'
        f'<desc id="desc">{escape(description)}</desc>'
        '<rect x="1" y="1" width="518" height="310" rx="8" fill="#071027" '
        'stroke="#52708e" stroke-width="1.5"/>'
        f'<text x="22" y="32" fill="#3db5ff" font-family="Arial,Helvetica,sans-serif" '
        f'font-size="21" font-weight="700">{escape(title)}</text>'
        f'<text x="497" y="32" text-anchor="end" fill="#a1b3ca" '
        f'font-family="Arial,Helvetica,sans-serif" font-size="11">{escape(subtitle)}</text>'
        '<path d="M22 48H498" stroke="#28405e"/>'
        + body
        + "</svg>\n"
    )


def make_cards(repos, now=None, merged_prs=None, opened_issues=None):
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=30)
    originals = sum(not item.get("fork", False) for item in repos)
    stars = sum(int(item.get("stargazers_count") or 0) for item in repos)
    active = 0
    for item in repos:
        pushed = item.get("pushed_at")
        if pushed:
            try:
                active += datetime.fromisoformat(pushed.replace("Z", "+00:00")) >= cutoff
            except (TypeError, ValueError):
                pass

    stamp = now.strftime("%Y-%m-%d")
    metrics = [
        ("Public repositories", len(repos)),
        ("Original projects", originals),
        ("Repository stars", stars),
        ("Merged public PRs", merged_prs),
        ("Public issues opened", opened_issues),
        ("Updated in 30 days", active),
    ]
    rows = []
    for i, (label, value) in enumerate(metrics):
        y = 85 + i * 39
        number = "N/A" if value is None else str(value)
        rows.append(
            f'<circle cx="29" cy="{y-5}" r="5" fill="#3db5ff" fill-opacity=".9"/>'
            f'<text x="44" y="{y}" fill="#cad7e8" font-family="Arial,Helvetica,sans-serif" '
            f'font-size="15">{escape(label)}</text>'
            f'<text x="490" y="{y}" text-anchor="end" fill="#ffffff" '
            f'font-family="Arial,Helvetica,sans-serif" font-size="20" font-weight="700">'
            f'{escape(number)}</text>'
        )
    stats = frame(
        "My GitHub Statistics", stamp, "".join(rows),
        "; ".join(f"{label}: {value if value is not None else 'unavailable'}"
                  for label, value in metrics) + ". Public data only."
    )

    counts = Counter(item.get("language") for item in repos if item.get("language"))
    top = counts.most_common(5)
    other = sum(counts.values()) - sum(c for _, c in top)
    if other:
        top.append(("Other", other))
    colors = {
        "TypeScript": "#8461ed", "JavaScript": "#f1e05a", "Python": "#3572a5",
        "Go": "#00add8", "CSS": "#d26ac2", "Other": "#8b949e",
    }
    palette = ["#8461ed", "#f1e05a", "#3572a5", "#00add8", "#d26ac2", "#8b949e"]
    count_all = sum(counts.values())
    body = [
        '<text x="22" y="75" fill="#9cacc5" font-family="Arial,Helvetica,sans-serif" '
        'font-size="12">Primary language per public repository</text>'
    ]
    if count_all:
        start = 23.0
        for i, (language, count) in enumerate(top):
            color = colors.get(language, palette[i % len(palette)])
            width = 474.0 * count / count_all
            body.append(
                f'<rect x="{start:.2f}" y="90" width="{width:.2f}" height="18" fill="{color}"/>'
            )
            start += width
        for i, (language, count) in enumerate(top):
            y = 140 + i * 27
            color = colors.get(language, palette[i % len(palette)])
            pct = 100.0 * count / count_all
            body.extend([
                f'<circle cx="29" cy="{y-5}" r="5.5" fill="{color}"/>',
                f'<text x="44" y="{y}" fill="#d4e0ed" font-family="Arial,Helvetica,sans-serif" '
                f'font-size="14">{escape(language)}</text>',
                f'<text x="492" y="{y}" text-anchor="end" fill="#ffffff" '
                f'font-family="Arial,Helvetica,sans-serif" font-size="14">'
                f'{count} repos ({pct:.1f}%)</text>',
            ])
    else:
        body.append(
            '<text x="22" y="132" fill="#9cacc5" font-family="Arial" '
            'font-size="15">No primary language data available.</text>'
        )
    language_card = frame(
        "Programming Languages", f"{count_all} classified repos", "".join(body),
        "; ".join(f"{language}: {count} repositories" for language, count in top)
        or "No primary languages identified."
    )
    return {"public-stats.svg": stats, "primary-languages.svg": language_card}


def main():
    repos = public_repositories()
    merged_prs = search_total(f"author:{USERNAME} is:pr is:merged is:public")
    opened_issues = search_total(f"author:{USERNAME} is:issue is:public")
    cards = make_cards(repos, merged_prs=merged_prs, opened_issues=opened_issues)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name, card in cards.items():
        (OUTPUT / name).write_text(card, encoding="utf-8")
    print(
        f"Updated {len(cards)} SVG cards from {len(repos)} public GitHub repositories. "
        f"Merged public PRs: {merged_prs}; public issues: {opened_issues}"
    )


if __name__ == "__main__":
    main()
