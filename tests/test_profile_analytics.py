"""Regression checks for the public GitHub profile SVG generator."""

import importlib.util
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "update_profile_analytics.py"
SPEC = importlib.util.spec_from_file_location("update_profile_analytics", SOURCE)
analytics = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(analytics)


class AnalyticsTests(unittest.TestCase):
    def test_reproducible_svg_and_public_metrics(self):
        sample = [
            {
                "fork": False, "language": "TypeScript", "stargazers_count": 2,
                "pushed_at": "2026-11-01T10:00:00Z",
            },
            {
                "fork": True, "language": "Python", "stargazers_count": 1,
                "pushed_at": "2025-04-01T10:00:00Z",
            },
            {
                "fork": False, "language": None, "stargazers_count": 0,
                "pushed_at": None,
            },
        ]
        when = datetime(2026, 11, 2, tzinfo=timezone.utc)
        cards = analytics.make_cards(sample, now=when, merged_prs=7, opened_issues=2)
        self.assertEqual(set(cards), {"public-stats.svg", "primary-languages.svg"})
        for text in cards.values():
            root = ET.fromstring(text)
            self.assertTrue(root.tag.endswith("svg"))
            self.assertIn('viewBox="0 0 520 312"', text)
        stats = cards["public-stats.svg"]
        self.assertIn("Public repositories: 3", stats)
        self.assertIn("Original projects: 2", stats)
        self.assertIn("Repository stars: 3", stats)
        self.assertIn("Merged public PRs: 7", stats)
        self.assertIn("Public issues opened: 2", stats)
        self.assertIn("Updated in 30 days: 1", stats)
        langs = cards["primary-languages.svg"]
        self.assertIn("TypeScript: 1 repositories", langs)
        self.assertIn("Python: 1 repositories", langs)
        self.assertIn("50.0%", langs)

    def test_missing_search_results_are_explicit(self):
        cards = analytics.make_cards(
            [], now=datetime(2026, 11, 2, tzinfo=timezone.utc),
            merged_prs=None, opened_issues=None,
        )
        self.assertIn("Merged public PRs: unavailable", cards["public-stats.svg"])
        self.assertIn("N/A", cards["public-stats.svg"])
        for graphic in cards.values():
            ET.fromstring(graphic)


if __name__ == "__main__":
    unittest.main()
