import logging
import shutil
from functools import partial
from pathlib import Path
from typing import Callable, Optional

import pandas as pd
from tqdm import tqdm

from ..utils.files import get_latest_file, timestamp_file
from .download import (
    get_compustat_gic_codes,
    get_compustat_quarterly,
    get_crsp_cfacshr,
    get_crsp_compu_link_table,
    get_crsp_daily,
    get_crsp_dates,
    get_crsp_monthly,
    get_ff5_factors,
    get_ff5_factors_monthly,
    get_ff_size_bp,
    get_ff_umd_factor_monthly,
    get_ibes_actuals,
    get_ibes_estimates,
    get_vix_daily,
    get_vrp_monthly,
)


def download_data(
    file: Path,
    name: str,
    download_func: Callable[[], pd.DataFrame],
    ignore_cache: bool = False,
    use_timestamping: bool = True,
) -> None:
    """
    Downloads data from a source and saves it to a file.

    Args:
        file (Path): The path to the file to save the data to.
        name (str): The name of the data being downloaded.
        download_func (Callable[[], pd.DataFrame]): A function that downloads the data and returns a pandas DataFrame.
        ignore_cache (bool, optional): Whether to ignore the cache and download the data again. Defaults to False.
    """
    logging.info(f"Downloading {name} data...")
    cached = file.exists()
    if use_timestamping:
        cached = get_latest_file(file) is not None
        file = timestamp_file(file)

    if not cached or ignore_cache:
        try:
            download_func().to_parquet(file)
        except Exception as e:
            logging.warning(f"{name} data download failed, skipping: {e}.")
        finally:
            logging.info(f"{name} data download complete to {file}.")
    else:
        logging.info(f"{name} data already downloaded, skipping.")


def download_files(
    cache_dir: Path,
    tmp_dir: Optional[Path] = None,
    ignore_cache: bool = False,
    fred_api_key: Optional[str] = None,
    wrds_username: Optional[str] = None,
    wrds_password: Optional[str] = None,
) -> None:
    """
    Downloads all necessary data files.

    Args:
        cache_dir (Path): The path to the cache directory.
        tmp_dir (Optional[Path], optional): The path to the temporary directory. Defaults to None.
        ignore_cache (bool, optional): Whether to ignore the cache and download the data again. Defaults to False.
        wrds_username (str, optional): The WRDS username to use for downloading CRSP data. Defaults to None.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    if tmp_dir is None:
        tmp_dir = cache_dir / "tmp"

    fails_tmp_dir = tmp_dir / "fails"
    fails_tmp_dir.mkdir(parents=True, exist_ok=True)

    DOWNLOAD_TASKS = [
        # Fama-French tasks
        {
            "file": cache_dir / "ff_size_breakpoints.parquet",
            "name": "Fama-French Size Breakpoints",
            "download_func": get_ff_size_bp,
        },
        {
            "file": cache_dir / "ff5_daily.parquet",
            "name": "Fama-French 5 Factors Daily",
            "download_func": get_ff5_factors,
        },
        {
            "file": cache_dir / "ff5_monthly.parquet",
            "name": "Fama-French 5 Factors Monthly",
            "download_func": get_ff5_factors_monthly,
        },
        {
            "file": cache_dir / "ff_umd_monthly.parquet",
            "name": "Fama-French UMD Factor Monthly",
            "download_func": get_ff_umd_factor_monthly,
        },
        # Yahoo Finance tasks
        {
            "file": cache_dir / "vix_daily.parquet",
            "name": "VIX Daily Data",
            "download_func": get_vix_daily,
        },
        # VRP tasks
        {
            "file": cache_dir / "vrp_monthly.parquet",
            "name": "VRP Monthly Data",
            "download_func": get_vrp_monthly,
        },
        # Compustat tasks
        {
            "file": cache_dir / "compustat_gic_codes.parquet",
            "name": "Compustat GIC Codes",
            "download_func": partial(
                get_compustat_gic_codes,
                wrds_username=wrds_username,
                wrds_password=wrds_password,
            ),
        },
        {
            "file": cache_dir / "compustat_quarterly.parquet",
            "name": "Compustat Quarterly Data",
            "download_func": partial(
                get_compustat_quarterly,
                wrds_username=wrds_username,
                wrds_password=wrds_password,
            ),
        },
        # CRSP tasks
        {
            "file": cache_dir / "crsp_daily.parquet",
            "name": "CRSP Daily Stock File",
            "download_func": partial(
                get_crsp_daily,
                wrds_username=wrds_username,
                wrds_password=wrds_password,
            ),
        },
        {
            "file": cache_dir / "crsp_monthly.parquet",
            "name": "CRSP Monthly Stock File",
            "download_func": partial(
                get_crsp_monthly,
                wrds_username=wrds_username,
                wrds_password=wrds_password,
            ),
        },
        {
            "file": cache_dir / "crsp_compu_link_table.parquet",
            "name": "CRSP-Compustat Link Table",
            "download_func": partial(
                get_crsp_compu_link_table,
                wrds_username=wrds_username,
                wrds_password=wrds_password,
            ),
        },
        {
            "file": cache_dir / "crsp_cfacshr.parquet",
            "name": "CRSP Adjustment Factors",
            "download_func": partial(
                get_crsp_cfacshr,
                wrds_username=wrds_username,
                wrds_password=wrds_password,
            ),
        },
        {
            "file": cache_dir / "crsp_dates.parquet",
            "name": "CRSP Trading Dates",
            "download_func": partial(
                get_crsp_dates,
                wrds_username=wrds_username,
                wrds_password=wrds_password,
            ),
        },
        # IBES tasks
        {
            "file": cache_dir / "ibes_estimates.parquet",
            "name": "IBES Analyst Estimates",
            "download_func": partial(
                get_ibes_estimates,
                wrds_username=wrds_username,
                wrds_password=wrds_password,
            ),
        },
        {
            "file": cache_dir / "ibes_actuals.parquet",
            "name": "IBES Actuals",
            "download_func": partial(
                get_ibes_actuals,
                wrds_username=wrds_username,
                wrds_password=wrds_password,
            ),
        },
    ]

    for task in tqdm(DOWNLOAD_TASKS, desc="Downloading"):
        download_data(
            file=task["file"],
            name=task["name"],
            download_func=task["download_func"],
            ignore_cache=ignore_cache,
        )

    # Cleanup
    shutil.rmtree(fails_tmp_dir)
