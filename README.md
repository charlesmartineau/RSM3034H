# RSM3034H - PhD Empirical Asset Pricing

This repository contains course materials for RSM3034H - PhD Empirical Asset Pricing.

> **Note on this branch:** this version of the repository only uses data that is
> freely available online (Fama-French, Yahoo Finance, VRP). All code that requires a
> WRDS subscription (CRSP, Compustat, IBES), along with the panel/event dataset
> construction and the figures and regression tables built on top of it, has been
> removed. Analysis that runs on the free data only, such as the Security Market Line
> figure, lives in `main_code/figures/`.

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
   cp .env_example .env
   ```

2. Edit `.env` and configure the following variables:

   **Required:**
   - `DATADIR`: Path to your data directory (must exist)

   **Optional (auto-created if not specified):**
   - `FIGDIR`: Directory for output figures (default: `./results_figures/`)
   - `TMP_DIR`: Temporary files directory (default: `./tmp/`)

   No API credentials or subscriptions are needed: every file downloaded here is
   publicly available.

### Running the Code

The pipeline is controlled by [main.py](main.py) and configured via [conf/config.yaml](conf/config.yaml).

Run it:

```bash
uv run main.py
```

With `data.download: true` in the config, this downloads the files below into
`DATADIR/download_cache/`, saving each one as a timestamped parquet file:

| File | Source |
| --- | --- |
| `ff_size_breakpoints.parquet` | Kenneth French's data library (NYSE size breakpoints) |
| `ff_bm_breakpoints.parquet` | Kenneth French's data library (book-to-market breakpoints) |
| `ff5_daily.parquet` | Fama-French 5 factors, daily |
| `ff5_monthly.parquet` | Fama-French 5 factors, monthly |
| `ff_umd_monthly.parquet` | Fama-French momentum (UMD) factor, monthly |
| `ff_25_size_bm_portfolios_daily.parquet` | Fama-French 25 size/BM portfolios, daily |
| `vix_daily.parquet` | VIX index from Yahoo Finance |
| `vrp_monthly.parquet` | Variance risk premium, monthly |
| `sp500_changes.parquet` | Additions to and removals from the S&P 500 (Wikipedia) |
| `sp500_addition_returns.parquet` | Daily Yahoo Finance returns around each addition since 2010 |

Downloads are cached: a file that is already present is skipped unless
`ignore_download_cache` is set to `true`. A source that is temporarily unreachable is
logged as a warning and skipped, so one failure does not stop the rest.

It then produces any figure switched on under `figures:` in the config, saving it to
`FIGDIR`. Each step is a separate flag, so once the data is cached you can rerun just
the figures with `data.download=false`.

Hydra writes a log of each run to a timestamped folder under [outputs/](outputs/).

## Configuration

All pipeline behavior is controlled by [conf/config.yaml](conf/config.yaml).

### `logging_level`

Integer log level passed to Python's `logging` module (default: `20` = INFO). Set to `10` for DEBUG or `30` for WARNING.

### `data`

- `download`: Download the raw data files into `DATADIR/download_cache/`. (default: `true`)
- `ignore_download_cache`: Force re-download even if cached files already exist. Useful when upstream data has been updated. (default: `false`)

### `figures`

Controls which figures are generated and saved to `FIGDIR`.

- `sml`: Plot the Security Market Line using the 25 size/BM portfolios as test assets. Average daily excess returns on the y-axis against CAPM betas on the x-axis, with both the SML implied by the CAPM and the line fitted across the 25 portfolios. Needs `ff_25_size_bm_portfolios_daily.parquet` and `ff5_daily.parquet` in the download cache. (default: `true`)
- `index_inclusion`: Plot the mean cumulative abnormal return around additions to the S&P 500 since 2010, over a `[-10, +20]` trading-day window with a 95% confidence band. Abnormal returns come from a market model estimated on the `[-250, -30]` window, and the standard errors are clustered by effective date, since S&P adds several firms at once. Needs `sp500_changes.parquet`, `sp500_addition_returns.parquet` and `ff5_daily.parquet` in the download cache. (default: `true`)

Any option can also be overridden on the command line, for example:

```bash
uv run main.py data.ignore_download_cache=true
```

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
  - [data/](main_code/data/) - Data downloading utilities
    - [download/](main_code/data/download/) - Data download modules
      - [famafrench.py](main_code/data/download/famafrench.py) - Kenneth French data library
      - [yahoo.py](main_code/data/download/yahoo.py) - Yahoo Finance (VIX)
      - [vrp.py](main_code/data/download/vrp.py) - Variance risk premium
      - [sp500_changes.py](main_code/data/download/sp500_changes.py) - S&P 500 index changes (Wikipedia) and the event-window returns from Yahoo Finance
    - [download_data.py](main_code/data/download_data.py) - Download orchestration and caching
  - [figures/](main_code/figures/) - Figure generation code
    - [sml.py](main_code/figures/sml.py) - Security Market Line using the 25 size/BM portfolios
    - [index_inclusion.py](main_code/figures/index_inclusion.py) - Event study of S&P 500 index inclusion since 2010
  - [utils/](main_code/utils/) - Utility functions
    - [files.py](main_code/utils/files.py) - File handling utilities (timestamping, latest-file lookup)

### Configuration & Output

- [conf/](conf/) - Configuration files
  - [config.yaml](conf/config.yaml) - Main configuration file for pipeline control
- [latex/](latex/) - LaTeX templates and styling
- [outputs/](outputs/) - Timestamped execution logs (organized by date and time)
- [results_figures/](results_figures/) - Output figures (configured via `FIGDIR` environment variable)
- [tmp/](tmp/) - Temporary files directory

### Data Directory Structure

The data directory (configured via `DATADIR` environment variable) contains:

- `download_cache/` - Cached downloaded files

### Other

- [logos/](logos/) - University and course branding
- [main.py](main.py) - Main execution script
