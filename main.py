import logging
import os
import time
from pathlib import Path
from typing import Tuple, Union

import hydra
import pandas as pd
from dotenv import load_dotenv
from omegaconf import DictConfig

from main_code.data import build_panel, compute_earning_surprises, download_files
from main_code.figures import plot_n_earnings_per_year, plot_n_stocks_per_year
from main_code.tables import create_ea_regression_table, oos_regression_example
from main_code.utils import configure_pyplot, get_latest_file, timestamp_file

load_dotenv()


def get_directories() -> Tuple[Path, Path, Path, Path, Path, Path, Path]:
    datadir_path = os.getenv("DATADIR")
    if not datadir_path:
        raise ValueError("DATADIR environment variable not set")

    fig_dir = Path(os.getenv("FIGDIR"))
    tab_dir = Path(os.getenv("TBLDIR"))

    data_dir = Path(datadir_path)
    download_dir = data_dir / "download_cache/"
    open_dir = data_dir / "open/"
    clean_dir = data_dir / "clean/"
    restricted_dir = data_dir / "restricted/"
    preprocess_dir = data_dir / "preprocess_cache/"

    tmp_dir = Path(os.getenv("TMP_DIR", "./tmp/"))

    fig_dir.mkdir(parents=True, exist_ok=True)
    tab_dir.mkdir(parents=True, exist_ok=True)
    download_dir.mkdir(parents=True, exist_ok=True)
    open_dir.mkdir(parents=True, exist_ok=True)
    clean_dir.mkdir(parents=True, exist_ok=True)
    restricted_dir.mkdir(parents=True, exist_ok=True)
    preprocess_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    return (
        fig_dir,
        tab_dir,
        data_dir,
        download_dir,
        open_dir,
        clean_dir,
        restricted_dir,
        preprocess_dir,
        tmp_dir,
    )


def get_credentials() -> Tuple[Union[str, None], Union[str, None], Union[str, None]]:
    fred_api_key = os.getenv("FRED_API_KEY")
    wrds_username = os.getenv("WRDS_USERNAME")
    wrds_password = os.getenv("WRDS_PASSWORD")

    return fred_api_key, wrds_username, wrds_password


@hydra.main(version_base=None, config_path="./conf", config_name="config")
def my_app(cfg: DictConfig):
    start_time = time.time()
    logging.getLogger().setLevel(cfg.logging_level)

    configure_pyplot(
        font_family=cfg.matplotlib.font.family,
        font_serif=cfg.matplotlib.font.serif,
        font_sans_serif=cfg.matplotlib.font.sans_serif,
    )

    (
        fig_dir,
        tab_dir,
        data_dir,
        download_dir,
        open_dir,
        clean_dir,
        restricted_dir,
        preprocess_dir,
        tmp_dir,
    ) = get_directories()

    fred_api_key, wrds_username, wrds_password = get_credentials()

    panel_path = clean_dir / "panel_data.parquet"

    # download files
    if cfg.data.download:
        download_files(
            cache_dir=download_dir,
            tmp_dir=tmp_dir,
            ignore_cache=cfg.data.ignore_download_cache,
            fred_api_key=fred_api_key,
            wrds_username=wrds_username,
            wrds_password=wrds_password,
        )

    if cfg.preprocess.compute_earning_surprises:
        logging.info("Computing earning surprises...")
        ea_surprises = compute_earning_surprises(download_dir, restricted_dir)
        ea_surprises_path = preprocess_dir / "ibes_sue.parquet"
        ea_surprises.to_parquet(
            timestamp_file(ea_surprises_path), index=False, engine="pyarrow"
        )
        logging.info(f"Earning surprises saved to {ea_surprises_path}")

    if cfg.tasks.build_panel:
        # build panel data
        logging.info("Building panel data...")
        panel = build_panel(
            download_dir, open_dir, restricted_dir, clean_dir, preprocess_dir
        )
        logging.info(f"Panel built. Shape: {panel.shape}")

        if cfg.tasks.save_panel:
            # save panel data

            panel.to_parquet(timestamp_file(panel_path), index=False, engine="pyarrow")
            logging.info(f"Panel data saved to {panel_path}")

    elif cfg.tasks.load_panel:
        # load existing panel data
        panel = pd.read_parquet(get_latest_file(panel_path))
        logging.info(f"Loaded existing panel data from {panel_path}")
    else:
        panel = None

    # Figure (requires panel)
    if cfg.figures.n_stocks_per_year:
        if panel is None:
            raise ValueError("Panel data required for n_stocks_per_year figure")
        logging.info("Creating figure: Number of stocks per year...")
        plot_n_stocks_per_year(panel, fig_dir)

    if cfg.figures.n_earnings_per_year:
        if panel is None:
            raise ValueError("Panel data required for n_earnings_per_year figure")
        logging.info("Creating figure: Number of earnings per year...")
        plot_n_earnings_per_year(panel, fig_dir)

    # Regression (requires panel)
    if cfg.tables.ea_regression:
        if panel is None:
            raise ValueError("Panel data required for ea_regression table")
        logging.info("Creating regression table: EA effect on excess returns...")
        create_ea_regression_table(panel, tab_dir)

    # OOS regression (uses download_cache, no panel required)
    if cfg.tables.oos_exmkt_vrp:
        logging.info("Creating OOS regression tables: Forecasting excess market returns using VRP...")
        oos_regression_example(download_dir, tab_dir, fig_dir)

    logging.info(f"Complete. Total runtime: {time.time() - start_time:.2f} seconds")


if __name__ == "__main__":
    my_app()
