# RSM3034H - PhD Empirical Asset Pricing

This repository contains course materials for RSM3034H - PhD Empirical Asset Pricing.

## Getting Started

### Prerequisites

- Python 3.12
- [uv](https://docs.astral.sh/uv/) (recommended) or pip for package management

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/RSM3034H.git
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

**Configuration Options** (edit [conf/config.yaml](conf/config.yaml)):

- **Data Download:**
  - `data.download`: Download data from WRDS and FRED (default: `false`)
  - `data.ignore_download_cache`: Force re-download even if cached (default: `false`)

- **Preprocessing:**
  - `preprocess.compute_earning_surprises`: Compute IBES earnings surprises (default: `false`)

- **Tasks:**
  - `tasks.build_panel`: Build the panel dataset from raw data (default: `false`)
  - `tasks.save_panel`: Save the built panel to disk (default: `false`)
  - `tasks.load_panel`: Load existing panel data (default: `true`)

- **Figures:**
  - `figures.n_stocks_per_year`: Generate plot showing number of stocks per year (default: `false`)

- **Tables:**
  - `tables.ea_regression`: Run earnings announcement regression analysis (default: `true`)

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
    - [download/](main_code/data/download/) - Data download modules (CRSP, Compustat, IBES, Fama-French, etc.)
    - [earnings/](main_code/data/earnings/) - Earnings-related data processing (IBES surprises, ICLINK)
    - [panel_data.py](main_code/data/panel_data.py) - Panel dataset construction
    - [download_data.py](main_code/data/download_data.py) - Main data download orchestration
  - [figures/](main_code/figures/) - Figure generation code
    - [n_stocks_per_year.py](main_code/figures/n_stocks_per_year.py) - Plot number of stocks over time
  - [tables/](main_code/tables/) - Table generation code
    - [ea_regression.py](main_code/tables/ea_regression.py) - Earnings announcement regression tables
    - [format.py](main_code/tables/format.py) - Table formatting utilities
  - [utils/](main_code/utils/) - Utility functions
    - [panel_ols_reg.py](main_code/utils/panel_ols_reg.py) - Panel OLS regression utilities
    - [files.py](main_code/utils/files.py) - File handling utilities
    - [pyplot_config.py](main_code/utils/pyplot_config.py) - Matplotlib configuration

### Configuration & Output

- [conf/](conf/) - Configuration files
  - [config.yaml](conf/config.yaml) - Main configuration file for pipeline control
- [latex/](latex/) - LaTeX templates and styling
- [outputs/](outputs/) - Timestamped execution outputs (organized by date and time)
- [results_figures/](results_figures/) - Output figures (configured via `FIGDIR` environment variable)
- [results_tables/](results_tables/) - Output tables (configured via `TBLDIR` environment variable)
- [tmp/](tmp/) - Temporary files directory

### Data Directory Structure

The data directory (configured via `DATADIR` environment variable) should contain:

- `download_cache/` - Cached downloaded files from WRDS and FRED
- `open/` - Open-access datasets
- `clean/` - Cleaned and processed datasets (includes `panel_data.parquet`)
- `restricted/` - Restricted-access datasets
- `preprocess_cache/` - Preprocessed data files (e.g., earnings surprises)

### Other

- [logos/](logos/) - University and course branding
- [main.py](main.py) - Main execution script orchestrating the entire pipeline

