# YelpFusion — Maryland Restaurant Data Collector

`yelpfusion.py` divides the State of Maryland into a 10 × 10 geographic grid and calls the **Yelp Fusion API** to catalogue every restaurant found in each cell.
The script writes duplicate-free CSVs, checkpoints its own progress so you can stop and resume at any time, and generates a high-resolution PNG/JPG map of the grid with search radii overlaid.

---

## Table of Contents

1. [Key Features](#key-features)
2. [Architecture & Data Flow](#architecture--data-flow)
3. [Quick Start](#quick-start)
4. [How It Works](#how-it-works)
5. [Repository Layout](#repository-layout)
6. [Configuration](#configuration)
7. [Troubleshooting](#troubleshooting)
8. [Contributing](#contributing)
9. [License](#license)

---

## Key Features

| Capability                 | Details                                                                                                                   |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| **10 × 10 grid**           | Covers 100 % of Maryland with cells ≈ 20 km × 40 km each.                                                                 |
| **Adaptive search radius** | Calculates the minimal radius (≤ 40 000 m, Yelp hard-limit) that encloses the cell’s diagonal plus a 20 % overlap margin. |
| **Stateful scraping**      | `maryland_grid_cells.csv` stores a `done` flag per cell, so an interrupted run resumes where it left off.                 |
| **Duplicate-free CSV**     | Each Yelp `business_id` is written exactly once, even if it appears in multiple cells.                                    |
| **Rate-limit defence**     | Detects HTTP 429, persists everything gathered so far, marks the current cell **not** done, and exits cleanly.            |
| **Cartographic output**    | Produces `maryland_grid_visualization.{png,jpg}` with OpenStreetMap tiles (via `contextily`).                             |
| **Automatic backups**      | Writes JSON snapshots every five cells and again when the last cell finishes.                                             |

---

## Architecture & Data Flow

```mermaid
flowchart TD
    A[Start] --> B[Load .env<br/>Yelp API key]
    B --> C{maryland_grid_cells.csv exists?}
    C -- No --> D[Generate 10×10 grid<br/>save CSV]
    C -- Yes --> E[Load grid<br/>with done flags]
    D --> F
    E --> F
    F[Render grid<br/>PNG/JPG] --> G[Load / init<br/>maryland_restaurants.csv]
    G --> H[Iterate over grid cells]
    H --> I{Cell marked done?}
    I -- Yes --> H
    I -- No --> J[Compute center & radius]
    J --> K[Call /businesses/search<br/>(paginated)]
    K --> L[Call /businesses/{id}<br/>full details]
    L --> M[Append NEW rows<br/>to CSV]
    M --> N[Mark cell done<br/>update CSV]
    N --> H
    H -->|every 5 cells| P[Write progress JSON]
    H -->|after last cell| Q[Write final JSON backup]
    Q --> R[Finish]
```

---

## Quick Start

```bash
# 1 — Clone the repo
git clone https://github.com/billy-enrizky/YelpFusion.git
cd YelpFusion

# 2 — (Recommended) create a virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 3 — Install dependencies
pip install -r requirements.txt

# 4 — Provide your Yelp key (https://developer.yelp.com/)
echo "YELP_API_KEY=YOUR_KEY_HERE" > .env

# 5 — Run the scraper
python yelpfusion.py
```

> **Tip:** The scraper is idempotent.
> If the process stops (power loss, 429, etc.), just run it again—completed cells are skipped automatically.

---

## How It Works

| Stage                   | Technical Notes                                                                                                                             |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| **Grid generation**     | Bounding box: lat 37.9171 → 39.72284, lon −79.4870 → −75.0506. Cell metadata (corners, centre, search radius) stored to CSV.                |
| **Radius calculation**  | Half-height & half-width in metres (`Δφ · 111 000`, `Δλ · 111 000 · cos φ`); diagonal × 1.2; capped at 40 000 m.                            |
| **API pagination**      | `/businesses/search` returns ≤ 50 rows; script increments `offset` (0, 50, 100, …) up to 1 000 rows per cell.                               |
| **Deduplication**       | A `set` of known Yelp IDs is loaded at startup and updated in-memory before each CSV append.                                                |
| **Rate-limit handling** | On HTTP 429: writes progress JSON, marks cell “no”, exits (`sys.exit(1)`).                                                                  |
| **Mapping**             | If `contextily` + `geopandas` are present, EPSG:4326 tiles from OpenStreetMap Mapnik are added; otherwise a plain matplotlib grid is drawn. |
| **Checkpoint cadence**  | `maryland_restaurants_progress.json` every 5 cells; `maryland_restaurants_json_backup.json` at completion.                                  |

---

## Repository Layout

| Path                                   | Purpose                                                 |
| -------------------------------------- | ------------------------------------------------------- |
| `yelpfusion.py`                        | Main orchestration script (grid, scrape, visualise).    |
| `requirements.txt`                     | Version-pinned Python dependencies.                     |
| `maryland_grid_cells.csv`              | Grid definition + `done` status (generated at runtime). |
| `maryland_restaurants.csv`             | Master list of deduplicated restaurants (generated).    |
| `maryland_grid_visualization.png/.jpg` | High-resolution map of the search grid (generated).     |
| `*_progress.json`, `*_backup.json`     | Incremental / final Yelp snapshots (generated).         |

---

## Configuration

### Mandatory environment variable

| Variable       | Description                                          |
| -------------- | ---------------------------------------------------- |
| `YELP_API_KEY` | Your personal Yelp Fusion API key (store in `.env`). |

### Optional constants (edit near the top of **`yelpfusion.py`**)

| Constant                         | Default                    | Meaning                                |
| -------------------------------- | -------------------------- | -------------------------------------- |
| `GRID_ROWS / GRID_COLS`          | `10 / 10`                  | Grid granularity.                      |
| `MD_NORTH / SOUTH / EAST / WEST` | Hard-coded Maryland bounds | Change these to scrape another region. |
| `timeout_s`                      | `5.0`                      | Yelp client timeout (seconds).         |

---

## Troubleshooting

| Symptom                   | Likely Cause                                | Fix                                                             |
| ------------------------- | ------------------------------------------- | --------------------------------------------------------------- |
| **401 Unauthorized**      | `YELP_API_KEY` missing or invalid.          | Verify key in `.env`.                                           |
| **429 Too Many Requests** | Daily quota or QPS exceeded.                | Wait for quota reset (midnight UTC) and rerun; scraper resumes. |
| **No map tiles**          | `contextily`/`geopandas` not installed.     | `pip install contextily geopandas`.                             |
| **Duplicate rows**        | Manual edits to `maryland_restaurants.csv`. | Remove duplicates or regenerate the CSV.                        |

---

## Contributing

1. Open an **Issue** describing the bug or feature.
2. Fork & create a branch: `git checkout -b feature/your-idea`.
3. Format code with **black** and run **flake8**.
4. Submit a concise, well-scoped **Pull Request**.

---

## License

Released under the **MIT License**.
Use of the Yelp Fusion API is governed by Yelp’s Developer Terms.

---

### Acknowledgements

* **Yelp Fusion API** for public restaurant data.
* **OpenStreetMap** contributors for map tiles served via `contextily`.
