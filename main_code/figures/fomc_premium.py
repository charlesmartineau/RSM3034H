"""
The picture that sells the FOMC announcement premium.

Cumulates the market excess return two ways on the same axes: the strategy that
holds the market only on scheduled FOMC announcement days, and the one that
holds it on every other day. About 3% of trading days account for a share of
the equity premium several times their weight, which is the whole result in one
line.
"""

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def plot_fomc_premium(df: pd.DataFrame, fig_dir: Path) -> None:
    """
    Plot the cumulative market excess return on FOMC days vs. all other days.

    Both series are cumulated over the same calendar, holding the risk-free
    asset when out of the market, so they are directly comparable and end at the
    total each group contributed to the equity premium.

    Args:
        df (pd.DataFrame): The daily panel from
            :func:`main_code.tables.fomc_premium.build_fomc_daily_panel`, with
            columns ``date``, ``mkt_rf`` (in percent) and ``fomc``.
        fig_dir (Path): Directory to save the figure.
    """
    data = df.dropna(subset=["mkt_rf"]).sort_values("date").reset_index(drop=True)

    # Back to decimals for compounding.
    excess = (data["mkt_rf"] / 100).to_numpy()
    on_fomc = np.where(data["fomc"] == 1, excess, 0.0)
    off_fomc = np.where(data["fomc"] == 0, excess, 0.0)

    cum_on = np.cumprod(1 + on_fomc)
    cum_off = np.cumprod(1 + off_fomc)
    cum_all = np.cumprod(1 + excess)

    n_fomc = int(data["fomc"].sum())
    logging.info(
        f"Cumulative excess return over {len(data):,} trading days: "
        f"all days {cum_all[-1]:.2f}x, "
        f"FOMC days only ({n_fomc} days) {cum_on[-1]:.2f}x, "
        f"other days only {cum_off[-1]:.2f}x"
    )

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.plot(
        data["date"],
        cum_all,
        linewidth=1.5,
        color="0.55",
        label=f"All days ({len(data):,} days)",
    )
    ax.plot(
        data["date"],
        cum_on,
        linewidth=2,
        color="C3",
        label=f"FOMC announcement days only ({n_fomc} days)",
    )
    ax.plot(
        data["date"],
        cum_off,
        linewidth=2,
        color="C0",
        label=f"All other days ({len(data) - n_fomc:,} days)",
    )

    ax.set_yscale("log")
    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative market excess return (\\$1 invested)")
    ax.set_title(
        "The FOMC announcement premium: "
        f"{n_fomc / len(data) * 100:.0f}\\% of trading days"
    )
    ax.axhline(y=1, color="black", linestyle="--", linewidth=0.8)
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.3)

    fig_path = fig_dir / "fomc_premium.pdf"
    plt.tight_layout()
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()

    logging.info(f"Figure saved to {fig_path}")
