# Maryland Restaurant Data Collection

A Python utility that divides the state of Maryland into a 10 × 10 grid, then uses the Yelp Fusion API to discover every restaurant inside each cell.
The script outputs clean, deduplicated CSV files, keeps track of progress so it can be resumed safely, and creates a map that shows the search grid.

---

## Table of Contents

1. [Key Features](#key-features)
2. [Quick Start](#quick-start)
3. [Detailed Workflow](#detailed-workflow)
4. [File Layout](#file-layout)
5. [Configuration](#configuration)
6. [Troubleshooting](#troubleshooting)
7. [Contributing](#contributing)
8. [License](#license)

---

## Key Features

| Capability                  | Description                                                                                                  |
| --------------------------- | ------------------------------------------------------------------------------------------------------------ |
| **10 × 10 geographic grid** | Covers all of Maryland with cells \~20 km × 40 km.                                                           |
| **Dynamic search radius**   | Calculates the minimum radius (capped at 40 km) needed to cover each cell.                                   |
| **Robust data collection**  | Paginates through Yelp results, avoids duplicates, and appends new businesses to `maryland_restaurants.csv`. |
| **Progress tracking**       | `maryland_grid_cells.csv` stores a `done` flag so interrupted runs can resume.                               |
| **Rate-limit handling**     | Detects HTTP 429 responses, saves current work, and exits gracefully.                                        |
| **Grid visualization**      | Generates `maryland_grid_visualization.png/.jpg`, including map tiles if `contextily` is installed.          |
| **Automatic backups**       | Writes JSON snapshots every five cells and at program end.                                                   |

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/billy-enrizky/YelpFusion
cd YelpFusion

# 2. Create and activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your Yelp API key to a .env file
echo "YELP_API_KEY=YOUR_API_KEY_HERE" > .env

# 5. Run the scraper
python yelpfusion.py
```

> **Tip:** The script is idempotent. If it stops for any reason, just run it again; completed grid cells will be skipped.

---

## Detailed Workflow

1. **Grid Creation**

   * Computes latitude/longitude bounds for each cell.
   * Stores metadata (corners, center point, search radius, completion status) in `maryland_grid_cells.csv`.

2. **Visualization**

   * Plots Maryland’s outline and every grid cell.
   * Adds OpenStreetMap tiles with `contextily` for easy orientation.

3. **Restaurant Search**

   * For each incomplete cell:

     * Calls the Yelp Fusion API with the pre-computed center point and radius.
     * Loops through result pages (`limit=50`, `offset` up to 950).
     * Fetches full business details for each ID, ensuring uniqueness across all cells.

4. **Data Storage**

   * Appends new rows to `maryland_restaurants.csv` with rich metadata: ratings, price tier, categories, address, coordinates, phone, and Yelp URL.
   * Saves JSON backups (`maryland_restaurants_progress.json`, `maryland_restaurants_json_backup.json`) for redundancy.

5. **Rate-Limit Protection**

   * On a 429 error, writes everything collected so far, flags the current cell as **not** done, and exits so you can retry later.

---

## File Layout

| Path                              | Purpose                                                     |
| --------------------------------- | ----------------------------------------------------------- |
| `maryland_restaurant_scraper.py`  | Main script (shown above).                                  |
| `requirements.txt`                | Pinned Python dependencies.                                 |
| `maryland_grid_cells.csv`         | Grid definition and progress log.                           |
| `maryland_restaurants.csv`        | Master table of all restaurants collected.                  |
| `maryland_grid_visualization.png` | High-resolution map of the grid (also saved as `.jpg`).     |
| `*_backup.json`                   | Incremental or final JSON backups of Yelp business objects. |

---

## Configuration

### Environment Variables

| Variable       | Description                                                                                                              |
| -------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `YELP_API_KEY` | **Required.** Your personal Yelp Fusion API key. See Yelp’s [Manage App](https://www.yelp.com/developers/v3/manage_app). |

### Optional Parameters

Edit the constants near the top of `maryland_restaurant_scraper.py` if you need to:

| Constant                | Default                 | Meaning                                        |
| ----------------------- | ----------------------- | ---------------------------------------------- |
| `GRID_ROWS / GRID_COLS` | `10 / 10`               | Number of grid divisions (≈ 20 × 40 km cells). |
| `MD_*`                  | Maryland lat/lon bounds | Geographic boundaries.                         |
| `timeout_s`             | `5.0`                   | Yelp API client timeout (seconds).             |

---

## Troubleshooting

| Symptom                                                 | Likely Cause                           | Fix                                                                           |
| ------------------------------------------------------- | -------------------------------------- | ----------------------------------------------------------------------------- |
| **Script exits with “429 Too Many Requests.”**          | Yelp daily quota or QPS limit reached. | Wait for quota reset, then rerun. The grid will pick up where it left off.    |
| **“contextily not found” warning and plain map image.** | Optional mapping libraries missing.    | `pip install contextily geopandas` for a tiled background map.                |
| **Duplicate businesses appear.**                        | Old CSV modified manually.             | Do not edit `maryland_restaurants.csv` by hand, or remove it and start fresh. |

---

## License

This project is licensed under the MIT License.
Use of the Yelp Fusion API is subject to Yelp’s terms of service and display requirements.

---

### Acknowledgements

* Yelp Fusion API team for free restaurant data.
* OpenStreetMap contributors for map tiles displayed via `contextily`.
