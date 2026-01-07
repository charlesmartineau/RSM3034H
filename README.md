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
python main.py
```

**Configuration Options** (edit [conf/config.yaml](conf/config.yaml)):

- `data.download`: Download data from WRDS and FRED (default: `true`)
- `data.ignore_download_cache`: Force re-download even if cached (default: `false`)
- `tasks.build_panel`: Build the panel dataset from raw data (default: `false`)
- `tasks.save_panel`: Save the built panel to disk (default: `false`)
- `analysis.summary_figures`: Generate summary figures (default: `false`)
- `analysis.news_predictor_reg`: Run news predictor regressions (default: `false`)

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
  - [figures/](main_code/figures/) - Figure generation code
  - [tables/](main_code/tables/) - Table generation code
  - [utils/](main_code/utils/) - Utility functions

### Configuration & Output

- [conf/](conf/) - Configuration files
- [latex/](latex/) - LaTeX templates and styling
- [outputs/](outputs/) - Generated outputs
- [results_figures/](results_figures/) - Output figures
- [results_tables/](results_tables/) - Output tables

### Other

- [logos/](logos/) - University and course branding
- [main.py](main.py) - Main execution script

