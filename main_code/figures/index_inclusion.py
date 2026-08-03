import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ..data.download.sp500_changes import (
    SAMPLE_START,
    get_sp500_additions,
    to_yahoo_ticker,
)
from ..utils.files import get_latest_file

# event window in trading days around the effective date
EVENT_START, EVENT_END = -10, 20

# market-model estimation window, ending well before the event window
EST_START, EST_END = -250, -30

# an event is kept only with a usable estimation window and a complete event window
MIN_EST_OBS = 100


def load_events(download_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load the S&P 500 additions, the event-window returns and the daily factors.

    Parameters
    ----------
    download_dir : Path
        Directory holding the downloaded files (``DATADIR/download_cache/``)

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]
        The additions since 2010, the daily stock returns and the daily factors
    """
    changes_file = get_latest_file(download_dir / "sp500_changes.parquet")
    returns_file = get_latest_file(download_dir / "sp500_addition_returns.parquet")
    ff5_file = get_latest_file(download_dir / "ff5_daily.parquet")

    if changes_file is None or returns_file is None or ff5_file is None:
        raise FileNotFoundError(
            "sp500_changes.parquet, sp500_addition_returns.parquet and "
            "ff5_daily.parquet are all required. Run main.py with "
            "data.download=true first."
        )

    additions = get_sp500_additions(pd.read_parquet(changes_file))
    # the returns were downloaded under the Yahoo Finance spelling of the ticker
    additions["ticker"] = additions["ticker"].map(to_yahoo_ticker)

    returns = pd.read_parquet(returns_file)
    factors = pd.read_parquet(ff5_file)[["date", "mkt_rf", "rf"]]

    return additions, returns, factors


def compute_abnormal_returns(
    additions: pd.DataFrame, returns: pd.DataFrame, factors: pd.DataFrame
) -> pd.DataFrame:
    """
    Compute market-model abnormal returns in event time for every addition.

    Event day 0 is the first trading day on or after the effective date. The
    market model is estimated on the ``[-250, -30]`` window,

        r_it - rf_t = alpha_i + beta_i * mkt_rf_t + e_it,

    and the abnormal return on event day tau is the residual evaluated out of
    sample. Events without enough estimation-window data, or with an incomplete
    event window, are dropped.

    Parameters
    ----------
    additions : pd.DataFrame
        Additions with columns ``date``, ``ticker``
    returns : pd.DataFrame
        Daily stock returns with columns ``ticker``, ``date``, ``ret``
    factors : pd.DataFrame
        Daily factors with columns ``date``, ``mkt_rf``, ``rf``

    Returns
    -------
    pd.DataFrame
        One row per (event, event day) with columns ``event_id``, ``ticker``,
        ``event_date``, ``tau``, ``ar``
    """
    panel = returns.merge(factors, on="date", how="inner")
    panel["excess_ret"] = panel["ret"] - panel["rf"]
    panel = panel.dropna(subset=["excess_ret", "mkt_rf"])

    by_ticker = {ticker: group.sort_values("date") for ticker, group in panel.groupby("ticker")}

    records = []
    dropped = 0
    for event_id, event in enumerate(additions.itertuples()):
        history = by_ticker.get(event.ticker)
        if history is None:
            dropped += 1
            continue

        dates = history["date"].to_numpy()
        # event day 0: the first trading day on or after the effective date
        day_zero = np.searchsorted(dates, np.datetime64(event.date), side="left")
        if day_zero == len(dates):
            dropped += 1
            continue

        tau = np.arange(len(dates)) - day_zero
        excess_ret = history["excess_ret"].to_numpy()
        mkt_rf = history["mkt_rf"].to_numpy()

        est = (tau >= EST_START) & (tau <= EST_END)
        evt = (tau >= EVENT_START) & (tau <= EVENT_END)

        if est.sum() < MIN_EST_OBS or evt.sum() < (EVENT_END - EVENT_START + 1):
            dropped += 1
            continue

        # market model: OLS of the excess return on the market excess return
        beta, alpha = np.polyfit(mkt_rf[est], excess_ret[est], 1)
        abnormal = excess_ret[evt] - (alpha + beta * mkt_rf[evt])

        records.append(
            pd.DataFrame(
                {
                    "event_id": event_id,
                    "ticker": event.ticker,
                    "event_date": event.date,
                    "tau": tau[evt],
                    "ar": abnormal,
                }
            )
        )

    if not records:
        raise RuntimeError("No addition had enough return data to be used.")

    logging.info(
        f"{len(records):,} usable events out of {len(additions):,} additions "
        f"({dropped:,} dropped: no Yahoo Finance history, too short an "
        f"estimation window, or a truncated event window)"
    )

    return pd.concat(records, ignore_index=True)


def compute_mean_car(abnormal_returns: pd.DataFrame) -> pd.DataFrame:
    """
    Cumulate the abnormal returns within each event, then average across events.

    The standard error is the cross-sectional standard deviation of the CAR on
    that event day divided by the square root of the number of events. It
    ignores the fact that firms added on the same day share market movements,
    so it understates the true sampling uncertainty.

    Parameters
    ----------
    abnormal_returns : pd.DataFrame
        Output of :func:`compute_abnormal_returns`

    Returns
    -------
    pd.DataFrame
        One row per event day with columns ``tau``, ``mean_car``, ``se``, ``n``
    """
    ar = abnormal_returns.sort_values(["event_id", "tau"]).copy()
    ar["car"] = ar.groupby("event_id")["ar"].cumsum()

    stats = ar.groupby("tau")["car"].agg(["mean", "std", "count"])
    stats.columns = ["mean_car", "std", "n"]
    stats["se"] = stats["std"] / np.sqrt(stats["n"])

    return stats.reset_index()[["tau", "mean_car", "se", "n"]]


def plot_index_inclusion(download_dir: Path, fig_dir: Path) -> None:
    """
    Plot the mean cumulative abnormal return around additions to the S&P 500
    since 2010.

    Shleifer (1986) and Harris and Gurel (1986) found a roughly 3% announcement
    return on index inclusion, which is striking because index membership
    carries no cash-flow news. Bennett, Stulz and Wang (JFE 2023) show the
    effect has essentially vanished since 2010, which is what this figure of the
    post-2010 additions should show.

    Two caveats to raise in class. Wikipedia records the *effective* date, not
    the announcement date, and S&P pre-announces roughly five business days
    earlier, so any run-up starts before day 0. And Yahoo Finance no longer
    serves prices for firms that were later acquired or delisted, so the sample
    is survivorship-tilted.

    Parameters
    ----------
    download_dir : Path
        Directory holding the downloaded files (``DATADIR/download_cache/``)
    fig_dir : Path
        Directory to save the figure
    """
    additions, returns, factors = load_events(download_dir)
    abnormal_returns = compute_abnormal_returns(additions, returns, factors)
    car = compute_mean_car(abnormal_returns)

    n_events = abnormal_returns["event_id"].nunique()
    first = abnormal_returns["event_date"].min()
    last = abnormal_returns["event_date"].max()

    # work in percent so the axis labels stay readable
    mean_car = car["mean_car"].values * 100
    se = car["se"].values * 100
    tau = car["tau"].values

    fig, ax = plt.subplots(figsize=(9, 6))

    ax.fill_between(
        tau,
        mean_car - 1.96 * se,
        mean_car + 1.96 * se,
        color="crimson",
        alpha=0.15,
        label="95% confidence band",
    )
    ax.plot(tau, mean_car, color="crimson", linewidth=1.8, label="Mean CAR")

    # the effective date, and the announcement roughly five business days earlier
    ax.axvline(0, color="black", linewidth=1.0, linestyle="--")
    ax.axvline(-5, color="gray", linewidth=0.9, linestyle=":")
    ax.axhline(0, color="black", linewidth=0.8, alpha=0.5)

    ax.annotate(
        "Effective date",
        (0, ax.get_ylim()[1]),
        textcoords="offset points",
        xytext=(4, -12),
        fontsize=8,
        color="dimgray",
    )
    ax.annotate(
        "Typical announcement\n(~5 business days earlier)",
        (-5, ax.get_ylim()[0]),
        textcoords="offset points",
        xytext=(-2, 14),
        fontsize=8,
        color="gray",
        ha="right",
    )

    ax.set_xlabel("Trading days relative to the effective date")
    ax.set_ylabel("Mean cumulative abnormal return (%)")
    ax.set_title(
        f"S&P 500 index inclusion: mean CAR around additions\n"
        f"{n_events:,} additions, {first:%b %Y} to {last:%b %Y}, "
        f"market model estimated on [{EST_START}, {EST_END}]",
        fontsize=11,
    )
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=9, loc="upper left", frameon=False)

    fig_path = fig_dir / "index_inclusion.pdf"
    plt.tight_layout()
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()

    for day in [-5, 0, 1, 5, 20]:
        row = car.loc[car["tau"] == day].squeeze()
        logging.info(
            f"CAR[{EVENT_START}, {day:+d}]: {row['mean_car'] * 100:+.2f}% "
            f"(t = {row['mean_car'] / row['se']:.2f}, n = {int(row['n'])})"
        )
    logging.info(f"Sample restricted to additions from {SAMPLE_START} on")
    logging.info(f"Figure saved to {fig_path}")
