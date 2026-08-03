import io
import logging

import pandas as pd
import requests
import yfinance as yf

from ...utils.files import get_latest_file

WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

# Wikipedia blocks requests that do not identify themselves
HEADERS = {"User-Agent": "RSM3034H course repository (academic use)"}

# the study only uses additions from this date on: Bennett, Stulz and Wang (JFE 2023)
# date the disappearance of the inclusion effect to around 2010
SAMPLE_START = "2010-01-01"

# calendar-day padding around each effective date, wide enough to contain the
# [-250, -30] estimation window and the [-10, +20] event window in trading days
DAYS_BEFORE = 420
DAYS_AFTER = 60


def get_sp500_changes() -> pd.DataFrame:
    """
    Scrape the "Selected changes to the list of S&P 500 components" table from
    Wikipedia and return it in long format.

    Each row of the Wikipedia table is one change and can carry both an addition
    and a removal, so it is unstacked into one row per (date, ticker, action).

    Returns
    -------
    pd.DataFrame
        Columns ``date``, ``ticker``, ``action`` (``"added"`` or ``"removed"``)
        and ``name``, sorted by date
    """
    response = requests.get(WIKI_URL, headers=HEADERS, timeout=60)
    response.raise_for_status()

    # table 0 is the current constituent list, table 1 is the change history
    changes = pd.read_html(io.StringIO(response.text))[1]
    changes.columns = [
        "date",
        "added_ticker",
        "added_name",
        "removed_ticker",
        "removed_name",
        "reason",
    ]

    # the dates are written out in full ("June 22, 2026")
    changes["date"] = pd.to_datetime(changes["date"], format="mixed", errors="coerce")
    changes = changes.dropna(subset=["date"])

    frames = []
    for action in ["added", "removed"]:
        side = changes[["date", f"{action}_ticker", f"{action}_name"]].copy()
        side.columns = ["date", "ticker", "name"]
        side = side.dropna(subset=["ticker"])
        side["action"] = action
        frames.append(side)

    out = pd.concat(frames, ignore_index=True)
    out["ticker"] = out["ticker"].str.strip().str.upper()
    out = out[["date", "ticker", "action", "name"]]

    return out.sort_values(["date", "action", "ticker"]).reset_index(drop=True)


def get_sp500_additions(changes: pd.DataFrame, start: str = SAMPLE_START) -> pd.DataFrame:
    """
    Keep the additions to the index from ``start`` on.

    Parameters
    ----------
    changes : pd.DataFrame
        The table returned by :func:`get_sp500_changes`
    start : str, optional
        First effective date to keep (default: 2010-01-01)

    Returns
    -------
    pd.DataFrame
        Columns ``date``, ``ticker``, ``name``, one row per addition
    """
    additions = changes[
        (changes["action"] == "added") & (changes["date"] >= pd.Timestamp(start))
    ]
    return additions[["date", "ticker", "name"]].reset_index(drop=True)


def to_yahoo_ticker(ticker: str) -> str:
    """Yahoo Finance writes share classes with a hyphen (BRK.B -> BRK-B)."""
    return ticker.replace(".", "-")


def get_sp500_addition_returns(cache_dir, chunk_size: int = 50) -> pd.DataFrame:
    """
    Download daily returns from Yahoo Finance around each S&P 500 addition since
    2010, and return them in long format.

    Reads the addition dates from the cached ``sp500_changes.parquet``, so
    :func:`get_sp500_changes` must have run first. Prices are downloaded in
    batches over the full sample span and then trimmed to a window around each
    effective date, which keeps the cached file small.

    Tickers that Yahoo no longer serves (firms acquired or delisted after being
    added) come back empty and are dropped; this is a survivorship caveat worth
    raising in class.

    Parameters
    ----------
    cache_dir : Path
        Directory holding the downloaded files (``DATADIR/download_cache/``)
    chunk_size : int, optional
        Number of tickers per Yahoo Finance request (default: 50)

    Returns
    -------
    pd.DataFrame
        Columns ``ticker``, ``date``, ``ret`` (simple daily return)
    """
    changes_file = get_latest_file(cache_dir / "sp500_changes.parquet")
    if changes_file is None:
        raise FileNotFoundError(
            "sp500_changes.parquet is required before the event-window returns "
            "can be downloaded."
        )

    additions = get_sp500_additions(pd.read_parquet(changes_file))
    logging.info(f"{len(additions):,} S&P 500 additions since {SAMPLE_START}")

    yahoo_tickers = sorted({to_yahoo_ticker(t) for t in additions["ticker"]})

    start = additions["date"].min() - pd.Timedelta(days=DAYS_BEFORE)
    end = additions["date"].max() + pd.Timedelta(days=DAYS_AFTER)

    prices = []
    for i in range(0, len(yahoo_tickers), chunk_size):
        chunk = yahoo_tickers[i : i + chunk_size]
        raw = yf.download(
            chunk,
            start=start,
            end=end,
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
        if raw.empty:
            continue
        # a single-ticker chunk comes back without the ticker level
        close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]]
        prices.append(close)

    if not prices:
        raise RuntimeError("Yahoo Finance returned no prices for any addition.")

    close = pd.concat(prices, axis=1).sort_index()
    close = close.dropna(axis=1, how="all")

    missing = sorted(set(yahoo_tickers) - set(close.columns))
    if missing:
        logging.warning(
            f"No Yahoo Finance prices for {len(missing)} tickers "
            f"(likely delisted or renamed): {', '.join(missing)}"
        )

    returns = (
        # fill_method=None: a missing price stays missing rather than being
        # carried forward into a spurious zero return
        close.pct_change(fill_method=None)
        .stack()
        .rename("ret")
        .reset_index()
        .rename(columns={"Date": "date", "Ticker": "ticker", "level_1": "ticker"})
    )
    returns["date"] = pd.to_datetime(returns["date"])

    # keep only the rows that some event window actually needs
    keep = pd.Series(False, index=returns.index)
    for row in additions.itertuples():
        keep |= (
            (returns["ticker"] == to_yahoo_ticker(row.ticker))
            & (returns["date"] >= row.date - pd.Timedelta(days=DAYS_BEFORE))
            & (returns["date"] <= row.date + pd.Timedelta(days=DAYS_AFTER))
        )

    returns = returns[keep].drop_duplicates(subset=["ticker", "date"])

    logging.info(
        f"Downloaded {len(returns):,} daily returns for "
        f"{returns['ticker'].nunique():,} tickers"
    )

    return returns[["ticker", "date", "ret"]].sort_values(["ticker", "date"]).reset_index(drop=True)
