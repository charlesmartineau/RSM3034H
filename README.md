# RSM3034H - PhD Empirical Asset Pricing

This repository contains course materials for RSM3034H - PhD Empirical Asset Pricing.

## Getting Started

### Prerequisites

- Python 3.12
- [uv](https://docs.astral.sh/uv/) (recommended) or pip for package management

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/charlesmartineau/RSM3034H.git
   cd RSM3034H
   ```

2. Install dependencies using uv (recommended):

   ```bash
   uv sync
   ```

   Or using pip:

   ```bash
   pip install -e .
   ```

### Environment Setup

1. Copy the example environment file:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and configure the following variables:

   **Required:**
   - `DATADIR`: Path to your data directory (must exist)

   **Optional (auto-created if not specified):**
   - `FIGDIR`: Directory for output figures (default: `./results_figures/`)
   - `TBLDIR`: Directory for output tables (default: `./results_tables/`)
   - `TMP_DIR`: Temporary files directory (default: `./tmp/`)

   **API Credentials (required for data downloads):**
   - `WRDS_USERNAME`: Your WRDS username
   - `WRDS_PASSWORD`: Your WRDS password
   - `FRED_API_KEY`: Your FRED API key from [https://fred.stlouisfed.org/docs/api/api_key.html](https://fred.stlouisfed.org/docs/api/api_key.html)

### Running the Code

The main analysis pipeline is controlled by [main.py](main.py) and configured via [conf/config.yaml](conf/config.yaml).

Run the analysis:

```bash
uv run main.py
```

Make sure to add this file [iclink](https://www.dropbox.com/scl/fi/katqy80qbake4rfohxv53/iclink.parquet?rlkey=21p75far2r27rz57gew5cuwx1&dl=0) to your `DATADIR/restricted/` directory before running the code.

## Configuration

All pipeline behavior is controlled by [conf/config.yaml](conf/config.yaml). Each option is a boolean flag (`true`/`false`) unless noted otherwise.

### `logging_level`

Integer log level passed to Python's `logging` module (default: `20` = INFO). Set to `10` for DEBUG or `30` for WARNING.

### `matplotlib`

Controls the default font used in all figures.

- `font.family`: Font family (`serif` or `sans-serif`).
- `font.serif`: List of serif fonts to try in order (default: `Computer Modern Roman`).
- `font.sans_serif`: List of sans-serif fonts to try in order (default: `Helvetica`).

### `data`

Controls data downloading from external sources (WRDS, FRED).

- `download`: Download raw data from WRDS and FRED into `DATADIR/download_cache/`. Set to `true` on first run or when refreshing data. (default: `false`)
- `ignore_download_cache`: Force re-download even if cached files already exist. Useful when upstream data has been updated. (default: `false`)

### `preprocess`

Controls preprocessing steps that transform raw downloads into intermediate files.

- `compute_earning_surprises`: Compute IBES earnings surprise (SUE) measure from raw IBES data and save to `DATADIR/preprocess_cache/ibes_sue.parquet`. Requires `data.download` to have run first. (default: `false`)

### `tasks`

Controls construction and loading of the main datasets. The pipeline supports two datasets: the **panel** (stock-month level) and the **event** dataset (earnings announcement windows).

**Panel data:**

- `build_panel`: Build the stock-month panel from downloaded and preprocessed files. (default: `false`)
- `save_panel`: Save the built panel to `DATADIR/clean/panel_data.parquet`. Only takes effect when `build_panel` is `true`. (default: `false`)
- `load_panel`: Load the most recent existing panel from disk instead of rebuilding it. Mutually exclusive with `build_panel`. (default: `false`)

**Event data:**

- `build_event_data`: Construct the earnings event dataset from the panel. Requires panel data to be available (either built or loaded). (default: `false`)
- `save_event_data`: Save the built event dataset to `DATADIR/clean/event_earnings_data.parquet`. Only takes effect when `build_event_data` is `true`. (default: `false`)
- `load_event_data`: Load the most recent existing event dataset from disk instead of rebuilding it. Mutually exclusive with `build_event_data`. (default: `true`)

### `figures`

Controls which figures are generated and saved to `FIGDIR`.

- `n_stocks_per_year`: Plot the number of stocks in the panel per calendar year. Requires panel data. (default: `false`)
- `n_earnings_per_year`: Plot the number of earnings announcements per calendar year. Requires panel data. (default: `false`)
- `event_study_earnings`: Plot the cumulative abnormal returns around earnings announcement dates. Requires event data. (default: `true`)
- `event_study_ann_ret`: Plot the event study by earnings announcement return quintile. Requires event data. (default: `false`)
- `fomc_premium`: Plot the cumulative market excess return split into scheduled FOMC announcement days vs. all other days. Uses data from `download_cache/` directly; does not require panel data. (default: `false`)

### `tables`

Controls which regression tables are generated and saved to `TBLDIR`.

- `ea_regression`: Run earnings announcement regressions (EA effect on excess returns) and export a LaTeX table. Requires panel data. (default: `false`)
- `oos_exmkt_vrp`: Run out-of-sample regression tables forecasting excess market returns using the variance risk premium. Uses data from `download_cache/` directly; does not require panel data. (default: `false`)
- `fomc_premium`: Run the time-series test of the FOMC announcement premium — the market excess return and the change in the VIX on a scheduled-FOMC-day dummy, daily, with Newey-West standard errors — and export `fomc_premium.tex` and `fomc_premium_summary.tex`. Uses `fomc_meetings.parquet`, `ff5_daily.parquet` and `vix_daily.parquet` from `download_cache/`; does not require panel data or WRDS. (default: `false`)

## The FOMC announcement premium

`tables.fomc_premium` and `figures.fomc_premium` implement the test of Savor and Wilson (JFQA 2013) and Lucca and Moench (JF 2015): essentially the entire equity premium is earned on the handful of scheduled macro announcement days, of which the ~8 FOMC days a year are the cleanest. It runs entirely on free data.

The sample starts **1994-02-04**. The FOMC only began announcing its policy decision on the day of the meeting in February 1994; before that the decision was inferred from open-market operations over the following days, so there is no announcement day to put a dummy on. `ff5_daily.parquet` starts in 1963, so the merge truncates the sample explicitly.

The announcement dummy is built from `fomc_meetings.parquet` under three rules:

1. a two-day meeting contributes **only its last day** — the statement is released at ~2:00pm ET on the second day, so `January 28-29` sets the dummy on the 29th
2. only regularly **scheduled** meetings count — conference calls, `(unscheduled)` meetings and `(notation vote)` entries are dropped, because their timing is endogenous to market conditions (the intermeeting cuts of January and October 2008, and March 2020)
3. **cancelled** meetings are dropped — the scheduled March 17-18, 2020 meeting never produced an announcement

The scraper is checked rather than trusted. The FOMC holds eight scheduled meetings per calendar year, which has held every year since 1994 with exactly one exception: 2020, which has seven. That check runs as a warning inside the downloader, so a silently changed Fed page shows up in the run log rather than in the regression, and as a test:

```bash
uv run pytest
```

The tests in [tests/test_fomc_dates.py](tests/test_fomc_dates.py) read `fomc_meetings.parquet` out of the download cache and are skipped if it is not there, so run `uv run main.py data.download=true` at least once first.

## Directory Structure

### Lecture Slides

- [lecture_slides/](lecture_slides/) - Quarto-based lecture presentations
  - [lecture01/](lecture_slides/lecture01/) - Cross-section
  - [lecture02/](lecture_slides/lecture02/) - Event Studies
  - [lecture03/](lecture_slides/lecture03/) - Macro Risk Premium
  - [lecture04/](lecture_slides/lecture04/) - Time Series
  - [lecture05/](lecture_slides/lecture05/) - Replication

### Code

- [main_code/](main_code/) - Main Python code directory
  - [data/](main_code/data/) - Data processing and loading utilities
    - [download/](main_code/data/download/) - Data download modules (CRSP, Compustat, IBES, Fama-French, FOMC, RavenPack, VRP, Yahoo Finance)
      - [fomc.py](main_code/data/download/fomc.py) - Scheduled FOMC meeting dates scraped from federalreserve.gov
    - [earnings/](main_code/data/earnings/) - Earnings-related data processing (IBES surprises, ICLINK)
    - [panel_data.py](main_code/data/panel_data.py) - Panel dataset construction
    - [event_data.py](main_code/data/event_data.py) - Earnings event dataset construction
    - [download_data.py](main_code/data/download_data.py) - Main data download orchestration
  - [figures/](main_code/figures/) - Figure generation code
    - [n_stocks_per_year.py](main_code/figures/n_stocks_per_year.py) - Plot number of stocks over time
    - [n_ea_per_year.py](main_code/figures/n_ea_per_year.py) - Plot number of earnings announcements over time
    - [event_study_earnings.py](main_code/figures/event_study_earnings.py) - Event study plot around earnings announcements
    - [fomc_premium.py](main_code/figures/fomc_premium.py) - Cumulative excess return on FOMC days vs. other days
  - [tables/](main_code/tables/) - Table generation code
    - [ea_regression.py](main_code/tables/ea_regression.py) - Earnings announcement regression tables
    - [oos_exmkt_vrp.py](main_code/tables/oos_exmkt_vrp.py) - Out-of-sample VRP forecasting regression tables
    - [fomc_premium.py](main_code/tables/fomc_premium.py) - FOMC announcement premium regression tables
    - [format.py](main_code/tables/format.py) - Table formatting utilities
  - [utils/](main_code/utils/) - Utility functions
    - [panel_ols_reg.py](main_code/utils/panel_ols_reg.py) - Panel OLS regression utilities
    - [files.py](main_code/utils/files.py) - File handling utilities
    - [pyplot_config.py](main_code/utils/pyplot_config.py) - Matplotlib configuration

### Configuration & Output

- [conf/](conf/) - Configuration files
  - [config.yaml](conf/config.yaml) - Main configuration file for pipeline control
- [latex/](latex/) - LaTeX templates and styling; [results.tex](latex/results.tex) `\input`s the tables from `results_tables/`
- [tests/](tests/) - Test suite (`uv run pytest`)
- [outputs/](outputs/) - Timestamped execution outputs (organized by date and time)
- [results_figures/](results_figures/) - Output figures (configured via `FIGDIR` environment variable)
- [results_tables/](results_tables/) - Output tables (configured via `TBLDIR` environment variable)
- [tmp/](tmp/) - Temporary files directory

### Data Directory Structure

The data directory (configured via `DATADIR` environment variable) should contain:

- `download_cache/` - Cached downloaded files from WRDS, FRED and the free sources (includes `fomc_meetings.parquet`, the scheduled FOMC announcement dates)
- `open/` - Open-access datasets
- `clean/` - Cleaned and processed datasets (includes `panel_data.parquet` and `event_earnings_data.parquet`)
- `restricted/` - Restricted-access datasets (place `iclink.parquet` here)
- `preprocess_cache/` - Preprocessed data files (e.g., `ibes_sue.parquet`)

### Other

- [logos/](logos/) - University and course branding
- [main.py](main.py) - Main execution script orchestrating the entire pipeline
