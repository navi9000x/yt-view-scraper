#!/usr/bin/env python3
import argparse
import re
import time
from typing import Optional, Dict, Tuple
from urllib.parse import quote_plus

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


# Matches things like:
# "1,234 views" / "12K views" / "1.2M views" / "3.4B views"
VIEW_RE = re.compile(
    r"""(?ix)
    (?P<num>\d+(?:\.\d+)?)
    \s*
    (?P<suffix>[kmb])?
    \s*
    views
    """
)


def parse_view_count(text: str) -> Optional[int]:
    """
    Convert strings like:
      "1,234 views" -> 1234
      "12K views"   -> 12000
      "1.2M views"  -> 1200000
      "3.4B views"  -> 3400000000
    Returns None if not parseable.
    """
    if not text:
        return None

    t = text.strip().lower().replace(",", "")
    m = VIEW_RE.search(t)
    if not m:
        return None

    num = float(m.group("num"))
    suffix = (m.group("suffix") or "").lower()

    mult = 1
    if suffix == "k":
        mult = 1_000
    elif suffix == "m":
        mult = 1_000_000
    elif suffix == "b":
        mult = 1_000_000_000

    return int(num * mult)


def extract_video_cards(page) -> Dict[str, int]:
    """
    Parse the currently loaded YouTube search results and return:
      { video_url: view_count_int }

    Dedupe by URL so rerenders / repeated cards don't double-count.
    """
    results: Dict[str, int] = {}

    cards = page.locator("ytd-video-renderer")
    count = cards.count()

    for i in range(count):
        card = cards.nth(i)

        # Get the video URL
        try:
            a = card.locator('a#video-title')
            href = a.get_attribute("href")
        except Exception:
            href = None

        if not href:
            continue

        url = ("https://www.youtube.com" + href) if href.startswith("/") else href

        # Skip if we've already captured this URL in this pass
        if url in results:
            continue

        # Metadata line usually contains: "X views • Y ago"
        views_text = ""
        try:
            meta_spans = card.locator("#metadata-line span").all_inner_texts()
            views_text = " • ".join([t.strip() for t in meta_spans if t.strip()])
        except Exception:
            views_text = ""

        vc = parse_view_count(views_text)

        # Fallback: scan any span text containing "views"
        if vc is None:
            try:
                spans = card.locator("span").all_inner_texts()
                candidate = " | ".join([s for s in spans if "views" in s.lower()])
                vc = parse_view_count(candidate)
            except Exception:
                vc = None

        if vc is not None:
            results[url] = vc

    return results


def scroll_and_collect(
    page,
    max_scrolls: int,
    scroll_pause: float,
    stable_rounds: int,
) -> Dict[str, int]:
    """
    Scrolls down to load more results. Each loop:
      - extracts video cards currently loaded
      - merges into all_results (deduped by URL)
      - scrolls to bottom

    Stops when:
      - max_scrolls reached, OR
      - unique URL count doesn't increase for stable_rounds consecutive scrolls
    """
    all_results: Dict[str, int] = {}
    stable = 0

    for n in range(max_scrolls):
        batch = extract_video_cards(page)
        before = len(all_results)

        # Merge (keep first seen view count for a URL)
        for url, views in batch.items():
            all_results.setdefault(url, views)

        after = len(all_results)
        gained = after - before

        if gained == 0:
            stable += 1
        else:
            stable = 0

        print(
            f"[scroll {n+1}/{max_scrolls}] "
            f"unique videos: {after} (+{gained}) "
            f"(stable={stable}/{stable_rounds})"
        )

        if stable >= stable_rounds:
            break

        # Scroll to bottom to trigger more loads
        page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
        time.sleep(scroll_pause)

    return all_results


def main():
    parser = argparse.ArgumentParser(
        description="Scrape YouTube search results and sum displayed view counts."
    )
    parser.add_argument(
        "-q", "--query",
        required=True,
        help="YouTube search query (use quotes for multiple words)."
    )
    parser.add_argument(
        "--max-scrolls",
        type=int,
        default=40,
        help="Maximum number of scrolls (default: 40)."
    )
    parser.add_argument(
        "--scroll-pause",
        type=float,
        default=1.3,
        help="Seconds to wait after each scroll (default: 1.3)."
    )
    parser.add_argument(
        "--stable-rounds",
        type=int,
        default=3,
        help="Stop after this many scrolls with no new unique videos (default: 3)."
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode."
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Print top N videos by views (default: 10)."
    )

    args = parser.parse_args()
    query = args.query.strip()

    search_url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
    print(f"Opening: {search_url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="en-US",
        )
        page = context.new_page()
        page.goto(search_url, wait_until="domcontentloaded")

        try:
            page.wait_for_selector("ytd-video-renderer", timeout=15_000)
        except PlaywrightTimeoutError:
            print("Search results did not load (no ytd-video-renderer found).")
            browser.close()
            return

        all_results = scroll_and_collect(
            page,
            max_scrolls=args.max_scrolls,
            scroll_pause=args.scroll_pause,
            stable_rounds=args.stable_rounds,
        )

        total = sum(all_results.values())

        print("\n=== Summary ===")
        print(f"Query: {query}")
        print(f"Videos parsed with view counts: {len(all_results)}")
        print(f"Total views (sum of displayed counts): {total:,}")

        if args.top and len(all_results) > 0:
            top_items: list[Tuple[str, int]] = sorted(
                all_results.items(), key=lambda kv: kv[1], reverse=True
            )[: args.top]

            print(f"\nTop {len(top_items)} videos by views:")
            for i, (url, views) in enumerate(top_items, 1):
                print(f"{i:>2}. {views:,}  {url}")

        browser.close()


if __name__ == "__main__":
    main()
