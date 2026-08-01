import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ..utils.files import get_latest_file


def load_test_assets(download_dir: Path) -> pd.DataFrame:
    """
    Load the 25 size/BM portfolios and the Fama-French factors, and merge them
    on the trading date.

    Parameters
    ----------
    download_dir : Path
        Directory holding the downloaded files (``DATADIR/download_cache/``)

    Returns
    -------
    pd.DataFrame
        Daily data with the 25 portfolio returns, ``mkt_rf`` and ``rf``
    """
    ff25_file = get_latest_file(download_dir / "ff_25_size_bm_portfolios_daily.parquet")
    ff5_file = get_latest_file(download_dir / "ff5_daily.parquet")

    if ff25_file is None or ff5_file is None:
        raise FileNotFoundError(
            "The 25 size/BM portfolios and the FF5 daily file are both required. "
            "Run main.py with data.download=true first."
        )

    ff25 = pd.read_parquet(ff25_file)
    ff5 = pd.read_parquet(ff5_file)

    # the FF5 file starts in 1963, the portfolios in 1926: the merge sets the window
    return ff25.merge(ff5[["date", "mkt_rf", "rf"]], on="date", how="inner")


def compute_capm_betas(data: pd.DataFrame) -> pd.DataFrame:
    """
    Compute the CAPM beta and the average excess return of each test asset.

    The beta is the slope of the time-series regression of the portfolio excess
    return on the market excess return, computed as cov(r_i - rf, mkt_rf) / var(mkt_rf).

    Parameters
    ----------
    data : pd.DataFrame
        Daily data returned by :func:`load_test_assets`

    Returns
    -------
    pd.DataFrame
        One row per portfolio with its beta, average excess return, size and BM quintile
    """
    port_cols = [col for col in data.columns if col.startswith("ff_size")]

    # the portfolio returns are total returns, so subtract the risk-free rate
    excess_ret = data[port_cols].sub(data["rf"], axis=0)
    mkt_rf = data["mkt_rf"]

    betas = excess_ret.apply(lambda ret: ret.cov(mkt_rf) / mkt_rf.var())

    results = pd.DataFrame(
        {
            "portfolio": port_cols,
            "beta": betas.values,
            "mean_excess_ret": excess_ret.mean().values,
        }
    )

    # ff_size3_bm2 -> size quintile 3, BM quintile 2
    results["size"] = results["portfolio"].str.extract(r"size(\d)").astype(int)
    results["bm"] = results["portfolio"].str.extract(r"bm(\d)").astype(int)
    results["label"] = "S" + results["size"].astype(str) + "B" + results["bm"].astype(str)

    return results


def plot_sml(download_dir: Path, fig_dir: Path) -> None:
    """
    Plot the Security Market Line using the 25 size/BM portfolios as test assets.

    Average daily excess returns are on the y-axis and CAPM betas on the x-axis,
    both in percent per day. The solid line is the SML implied by the CAPM; the
    dashed line is fitted across the 25 portfolios.

    Parameters
    ----------
    download_dir : Path
        Directory holding the downloaded files (``DATADIR/download_cache/``)
    fig_dir : Path
        Directory to save the figure
    """
    data = load_test_assets(download_dir)
    results = compute_capm_betas(data)

    start, end = data["date"].min(), data["date"].max()
    logging.info(
        f"SML estimated on {len(data):,} daily observations, "
        f"{start:%Y-%m-%d} to {end:%Y-%m-%d}"
    )

    # work in percent per day so the axis labels stay readable
    beta = results["beta"].values
    mean_ret = results["mean_excess_ret"].values * 100
    mean_mkt = data["mkt_rf"].mean() * 100

    fig, ax = plt.subplots(figsize=(9, 6))

    beta_grid = np.linspace(0, beta.max() * 1.1, 100)

    # the SML predicted by the CAPM: through the origin and the market portfolio
    ax.plot(
        beta_grid,
        beta_grid * mean_mkt,
        color="black",
        linewidth=1.5,
        label="CAPM SML",
        zorder=1,
    )

    # the line actually fitted by the 25 portfolios
    slope, intercept = np.polyfit(beta, mean_ret, 1)
    ax.plot(
        beta_grid,
        intercept + slope * beta_grid,
        color="crimson",
        linestyle="--",
        linewidth=1.5,
        label="Fitted cross-sectional line",
        zorder=1,
    )

    # the market portfolio sits at beta = 1 by construction
    ax.scatter(
        [1],
        [mean_mkt],
        marker="*",
        s=250,
        color="black",
        label="Market",
        zorder=3,
    )

    colors = plt.cm.viridis(np.linspace(0, 0.85, 5))
    for size_quintile, group in results.groupby("size"):
        ax.scatter(
            group["beta"],
            group["mean_excess_ret"] * 100,
            color=colors[size_quintile - 1],
            s=60,
            edgecolor="white",
            linewidth=0.5,
            label=f"Size {size_quintile}",
            zorder=2,
        )

    # several portfolios sit almost on top of each other, so alternate the label
    # offset to keep them legible
    for i, row in enumerate(results.itertuples()):
        ax.annotate(
            row.label,
            (row.beta, row.mean_excess_ret * 100),
            textcoords="offset points",
            xytext=(6, 4) if i % 2 == 0 else (6, -9),
            fontsize=6,
            color="dimgray",
        )

    ax.set_xlabel("CAPM beta")
    ax.set_ylabel("Average daily excess return (%)")
    ax.set_title(
        f"Security Market Line: 25 size/BM portfolios\n"
        f"{start:%b %Y} to {end:%b %Y}",
        fontsize=11,
    )
    ax.grid(True, alpha=0.3)
    # outside the axes: the points fill most of the plotting area
    ax.legend(fontsize=8, loc="upper left", bbox_to_anchor=(1.02, 1), frameon=False)

    fig_path = fig_dir / "sml.pdf"
    plt.tight_layout()
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()

    logging.info(
        f"CAPM SML slope: {mean_mkt:.4f}%/day, fitted slope: {slope:.4f}%/day "
        f"(intercept {intercept:.4f}%/day)"
    )
    logging.info(f"Figure saved to {fig_path}")
