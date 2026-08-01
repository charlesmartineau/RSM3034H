import logging
import os
import time
from pathlib import Path

import hydra
from dotenv import load_dotenv
from omegaconf import DictConfig

from main_code.data import download_files
from main_code.figures import plot_sml

load_dotenv()


def get_directories() -> tuple[Path, Path, Path]:
    datadir_path = os.getenv("DATADIR")
    if not datadir_path:
        raise ValueError("DATADIR environment variable not set")

    data_dir = Path(datadir_path)
    download_dir = data_dir / "download_cache/"

    fig_dir = Path(os.getenv("FIGDIR", "./results_figures/"))
    tmp_dir = Path(os.getenv("TMP_DIR", "./tmp/"))

    download_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    return download_dir, fig_dir, tmp_dir


@hydra.main(version_base=None, config_path="./conf", config_name="config")
def my_app(cfg: DictConfig):
    start_time = time.time()
    logging.getLogger().setLevel(cfg.logging_level)

    download_dir, fig_dir, tmp_dir = get_directories()

    # download the freely available data files
    if cfg.data.download:
        download_files(
            cache_dir=download_dir,
            tmp_dir=tmp_dir,
            ignore_cache=cfg.data.ignore_download_cache,
        )

    # figures
    if cfg.figures.sml:
        logging.info("Creating figure: Security Market Line...")
        plot_sml(download_dir, fig_dir)

    logging.info(f"Complete. Total runtime: {time.time() - start_time:.2f} seconds")


if __name__ == "__main__":
    my_app()
