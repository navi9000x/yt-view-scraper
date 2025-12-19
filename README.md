# YouTube Search View Counter

This tool scrapes YouTube search results, extracts the **displayed view counts** for each video (including suffixes like `K`, `M`, `B`), automatically scrolls to load more results, deduplicates videos by URL, and reports the **total summed views**.

It is designed for exploratory analysis of how much aggregate attention a search term has received on YouTube.

---

## What This Script Does

- Opens a YouTube search results page
- Scrolls the page to load more videos (infinite scroll)
- Extracts view counts from each video card
- Correctly parses:
  - `1,234 views`
  - `12K views`
  - `1.2M views`
  - `3.4B views`
- Deduplicates videos by URL
- Stops automatically when results become “stable”
- Prints:
  - Total number of videos parsed
  - Sum of displayed view counts
  - Top N videos by views

---

## Requirements

- Python **3.9+**
- Google Chrome / Chromium
- Playwright (Python)

---

## Installation

### 1. Install dependencies
```bash
pip install playwright
```

### 2. Install the browser engine
```bash
playwright install chromium
```

---

## Basic Usage

Run the script with a search query:

```bash
python yt_views_sum.py -q "strawberry elephant"
```

This will:
- Search YouTube for **“strawberry elephant”**
- Scroll the results page
- Aggregate view counts
- Print a summary to the terminal

---

## Example Output

```
Opening: https://www.youtube.com/results?search_query=strawberry+elephant
[scroll 1/40] unique videos: 18 (+18) (stable=0/3)
[scroll 2/40] unique videos: 34 (+16) (stable=0/3)
[scroll 3/40] unique videos: 48 (+14) (stable=0/3)
...
[scroll 9/40] unique videos: 121 (+0) (stable=3/3)

=== Summary ===
Query: strawberry elephant
Videos parsed with view counts: 121
Total views (sum of displayed counts): 84,312,000
```

---

## Command-Line Options

| Flag | Description | Default |
|----|----|----|
| `-q`, `--query` | YouTube search query | required |
| `--max-scrolls` | Maximum number of scroll events | `40` |
| `--scroll-pause` | Seconds to wait after each scroll | `1.3` |
| `--stable-rounds` | Stop after N scrolls with no new videos | `3` |
| `--headless` | Run browser without UI | off |
| `--top` | Show top N videos by views | `10` |

### Examples

Limit scrolling:
```bash
python yt_views_sum.py -q "strawberry elephant" --max-scrolls 15
```

Run headless:
```bash
python yt_views_sum.py -q "strawberry elephant" --headless
```

Show more top results:
```bash
python yt_views_sum.py -q "strawberry elephant" --top 25
```

---

## What “Stable” Means

YouTube uses **infinite scrolling**, not pages.

The script tracks how many **new unique videos** appear after each scroll.

- If a scroll adds **zero new videos**, it is considered **stable**
- After `stable-rounds` consecutive stable scrolls, scrolling stops
- This prevents infinite scrolling when YouTube has no more results to load

---

## Accuracy Notes

- The script sums **displayed view counts**, which are often rounded
  - `1.2M` is treated as `1,200,000`
- Live videos, “No views”, or unusual formats may be skipped
- Results depend on:
  - Region
  - Language
  - YouTube UI changes

This tool is best suited for **relative comparisons and trend exploration**, not exact accounting.

---

## Common Use Cases

- Estimating total attention for a keyword or meme
- Comparing search result saturation across topics
- Identifying whether views are concentrated in a few viral videos
- Rapid research without API keys

---

## File Overview

- `yt_views_sum.py` — main script
- `README.md` — usage and documentation

---

## Notes

If YouTube displays a consent or cookie dialog on first run:
- Run without `--headless`
- Accept once
- Re-run the script

---

## License

Use freely for research, experimentation, and internal analysis.
