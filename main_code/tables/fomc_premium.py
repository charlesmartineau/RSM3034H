"""
The FOMC announcement premium.

Savor and Wilson (JFQA 2013) show that essentially the entire equity premium is
earned on a handful of scheduled macroeconomic announcement days.  Lucca and
Moench (JF 2015) sharpen it: the excess return accrues in the 24 hours *before*
the FOMC statement, not after it.  Roughly 80% of the post-1994 equity premium
is earned on the ~8 scheduled FOMC days a year -- about 3% of trading days.

The test is deliberately simple, which is the teaching point:

.. code::

    r_mkt,t - rf_t = a + b * D^FOMC_t + e_t
    dvix_t         = a + b * D^FOMC_t + e_t

with ``D^FOMC_t = 1`` on scheduled FOMC announcement days, at daily frequency,
with Newey-West standard errors.  The FOMC calendar is published a year ahead,
so the regressor is known ex ante: there is no look-ahead bias and nothing to
mine.  What there *is* is a power problem -- eight treated days a year -- which
is what the standard errors are there to make visible.

The sample starts 1994-02-04.  The FOMC only began announcing its policy
decision on the day of the meeting in February 1994; before that the decision
was inferred from open-market operations over the following days, so there is
no announcement day to put a dummy on and the test is not defined.
``ff5_daily.parquet`` starts in 1963, so the sample has to be truncated
explicitly rather than left to whatever the factor file happens to contain.

One thing to flag when reading the leads and lags: Lucca and Moench date the
drift to the 24 hours before the 2:00pm ET statement, but that window runs from
the day -1 *close* to the day 0 close, so in close-to-close daily returns it
shows up on day 0, not on day -1. Separating the two needs intraday data.
"""

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from ..utils import ols_reg_hac
from ..utils.files import get_latest_file
from .format import regression_table, reorder_reg_output

# The FOMC began announcing its decision on the day of the meeting in Feb 1994.
SAMPLE_START = "1994-02-04"

# Press conferences after every meeting begin in April 2011, which is the
# natural place to split the sample.
SUBSAMPLE_SPLIT = "2011-01-01"

# Newey-West lags: one trading week.
HAC_MAXLAGS = 5

TRADING_DAYS_PER_YEAR = 252

# Display names, kept in sync with utils.PREFIX_MAP.
FOMC = r"$1_{FOMC}$"
FOMC_M1 = r"$1_{FOMC,-1}$"
FOMC_P1 = r"$1_{FOMC,+1}$"
INTERCEPT = "Intercept"

DEP_EXMKT = r"$Ret^M-R_f$ (\%)"
DEP_DVIX = r"$\Delta VIX$"
DEP_VIX = r"$VIX$"


def build_fomc_daily_panel(download_dir: Path) -> pd.DataFrame:
    """
    Build the daily 1994-onward panel the FOMC regressions run on.

    Merges the scheduled FOMC announcement dates onto the daily Fama-French
    factors and the VIX, and builds the announcement dummy along with its
    event-time neighbours.

    Args:
        download_dir (Path): The download cache directory.

    Returns:
        pd.DataFrame: One row per trading day from 1994-02-04, with columns
            ``date``, ``mkt_rf`` (market excess return, in percent), ``vix``,
            ``delta_vix``, and the dummies ``fomc_m1``, ``fomc``, ``fomc_p1``.
    """
    fomc = pd.read_parquet(get_latest_file(download_dir / "fomc_meetings.parquet"))
    ff = pd.read_parquet(get_latest_file(download_dir / "ff5_daily.parquet"))
    vix = pd.read_parquet(get_latest_file(download_dir / "vix_daily.parquet"))

    # Only regularly scheduled meetings go into the dummy. Conference calls,
    # unscheduled meetings and notation votes are timed in response to market
    # conditions -- the intermeeting cuts of January and October 2008 and of
    # March 2020 -- so including them would contaminate the premium with the
    # crises that caused them.
    announcements = fomc.loc[fomc["scheduled"], ["date"]].drop_duplicates()
    logging.info(
        f"{len(announcements)} scheduled FOMC announcement dates on the calendar"
    )

    df = ff[["date", "mkt_rf"]].merge(vix[["date", "vix"]], on="date", how="left")
    df = df.sort_values("date").reset_index(drop=True)

    # mkt_rf is already the market excess return; put it in percent.
    df["mkt_rf"] = df["mkt_rf"] * 100
    df["delta_vix"] = df["vix"].diff()

    df["fomc"] = df["date"].isin(announcements["date"]).astype(int)

    # Leads and lags in event time on the *trading*-day calendar, not the
    # calendar-day one: fomc_m1 marks the trading day before the announcement,
    # which is the pre-FOMC drift window of Lucca and Moench.
    df["fomc_m1"] = df["fomc"].shift(-1).fillna(0).astype(int)
    df["fomc_p1"] = df["fomc"].shift(1).fillna(0).astype(int)

    # Truncate to the announcement era. The diff and the shifts above are taken
    # on the full series first so the first in-sample day is not lost.
    df = df[df["date"] >= SAMPLE_START].reset_index(drop=True)

    n_matched = int(df["fomc"].sum())
    n_expected = int(
        announcements["date"].between(df["date"].min(), df["date"].max()).sum()
    )
    if n_matched != n_expected:
        # Announcement dates that are not trading days in the factor file, e.g.
        # dates on the forward calendar that have not happened yet.
        logging.warning(
            f"{n_expected - n_matched} scheduled announcement dates did not match a "
            f"trading day in ff5_daily between {df['date'].min():%Y-%m-%d} and "
            f"{df['date'].max():%Y-%m-%d}"
        )

    logging.info(
        f"FOMC daily panel: {len(df):,} trading days, {n_matched} FOMC announcement days "
        f"({n_matched / len(df) * 100:.1f}% of days), "
        f"{df['date'].min():%Y-%m-%d} to {df['date'].max():%Y-%m-%d}"
    )

    return df


def compute_fomc_summary_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    Summary statistics to report alongside the regression table.

    Reports the number of FOMC days, the mean market excess return on and off
    announcement days, the annualized Sharpe ratio of each, and the fraction of
    the total equity premium earned on FOMC days.

    Args:
        df (pd.DataFrame): The daily panel from :func:`build_fomc_daily_panel`.

    Returns:
        pd.DataFrame: Statistics by group, ready to write out.
    """
    sample = df[df["mkt_rf"].notnull()]

    on = sample.loc[sample["fomc"] == 1, "mkt_rf"]
    off = sample.loc[sample["fomc"] == 0, "mkt_rf"]

    # Total cumulated excess return, in percent, split by group. This is the
    # "fraction of the equity premium earned on FOMC days" denominator.
    total = sample["mkt_rf"].sum()

    def sharpe(returns: pd.Series) -> float:
        return returns.mean() / returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR)

    stats = pd.DataFrame(
        {
            "FOMC days": [
                len(on),
                on.mean(),
                on.mean() * 100,
                sharpe(on),
                on.sum() / total * 100,
            ],
            "Other days": [
                len(off),
                off.mean(),
                off.mean() * 100,
                sharpe(off),
                off.sum() / total * 100,
            ],
            "All days": [
                len(sample),
                sample["mkt_rf"].mean(),
                sample["mkt_rf"].mean() * 100,
                sharpe(sample["mkt_rf"]),
                100.0,
            ],
        },
        index=[
            "N days",
            r"Mean $Ret^M-R_f$ (\%)",
            r"Mean $Ret^M-R_f$ (bps)",
            "Annualized Sharpe ratio",
            r"Share of equity premium (\%)",
        ],
    )

    logging.info("FOMC announcement premium, summary statistics:\n%s", stats.to_string())

    return stats


def write_summary_table(stats: pd.DataFrame, tab_dir: Path) -> Path:
    """Write the summary statistics as a standalone LaTeX tabular."""
    formatted = stats.astype(object)
    formatted.loc["N days"] = stats.loc["N days"].map(lambda x: f"{x:,.0f}")
    for row in formatted.index.drop("N days"):
        formatted.loc[row] = stats.loc[row].map(lambda x: f"{x:.2f}")

    table_path = tab_dir / "fomc_premium_summary.tex"
    formatted.to_latex(table_path, escape=False, column_format="lccc")
    logging.info(f"Table saved to {table_path}")

    return table_path


def _notes(df: pd.DataFrame, stats: pd.DataFrame) -> str:
    """The notes block that travels with the regression table."""
    n_fomc = int(stats.loc["N days", "FOMC days"])
    share = stats.loc[r"Share of equity premium (\%)", "FOMC days"]

    return (
        "\n\\vspace{0.75em}\n"
        "\\begin{minipage}{\\textwidth}\n"
        "\\footnotesize\n"
        "\\textit{Notes.} Daily frequency. The sample runs from "
        f"{pd.Timestamp(SAMPLE_START):%B~%-d, %Y}, the first FOMC meeting whose "
        "policy decision was announced on the day of the meeting, through "
        f"{df['date'].max():%B~%-d, %Y}, and contains {len(df):,} trading days of "
        f"which {n_fomc} are scheduled FOMC announcement days "
        f"({n_fomc / len(df) * 100:.1f}\\% of days, earning "
        f"{share:.0f}\\% of the cumulated equity premium). "
        "$1_{FOMC}$ equals one on the announcement day, which is the "
        "\\emph{last} day of a two-day meeting; $1_{FOMC,-1}$ and $1_{FOMC,+1}$ "
        "equal one on the trading day before and after it. Conference calls, "
        "unscheduled meetings, notation votes and the cancelled March 2020 "
        "meeting are excluded. Columns (1)--(5) are in percent per day. "
        f"Newey-West standard errors with {HAC_MAXLAGS} lags in parentheses. "
        "*, ** and *** denote significance at the 10\\%, 5\\% and 1\\% level.\n"
        "\\end{minipage}\n"
    )


def run_fomc_premium(
    download_dir: Path, tab_dir: Path, df: Optional[pd.DataFrame] = None
) -> pd.DataFrame:
    """
    Run the FOMC announcement premium regressions and write the LaTeX table.

    Estimates, all with Newey-West standard errors on the daily 1994-onward
    sample:

    1. the baseline premium, market excess return on the FOMC dummy
    2. leads and lags, to locate *when* the return accrues
    3. and 4. the two press-conference-era subsamples, and the sample dropping
       the financial crisis
    5. the volatility side: the change in the VIX, and the VIX level

    Args:
        download_dir (Path): The download cache directory.
        tab_dir (Path): Directory to save the table.
        df (pd.DataFrame, optional): A daily panel already built by
            :func:`build_fomc_daily_panel`, to avoid building it twice when the
            companion figure is produced in the same run. Built here if omitted.

    Returns:
        pd.DataFrame: The assembled regression output.
    """
    if df is None:
        df = build_fomc_daily_panel(download_dir)

    stats = compute_fomc_summary_stats(df)
    write_summary_table(stats, tab_dir)

    early = df[df["date"] < SUBSAMPLE_SPLIT]
    late = df[df["date"] >= SUBSAMPLE_SPLIT]
    # Dropping the crisis: the intermeeting cuts of 2008 are already excluded
    # from the dummy, but 2008-09 still dominates the sample variance.
    ex_crisis = df[~df["date"].dt.year.isin([2008, 2009])]

    specs = [
        (df, "mkt_rf~1+fomc", DEP_EXMKT),
        (df, "mkt_rf~1+fomc_m1+fomc+fomc_p1", DEP_EXMKT),
        (early, "mkt_rf~1+fomc", DEP_EXMKT),
        (late, "mkt_rf~1+fomc", DEP_EXMKT),
        (ex_crisis, "mkt_rf~1+fomc", DEP_EXMKT),
        (df.dropna(subset=["delta_vix"]), "delta_vix~1+fomc", DEP_DVIX),
        (df.dropna(subset=["vix"]), "vix~1+fomc", DEP_VIX),
    ]

    reg_df = pd.concat(
        [ols_reg_hac(data, formula, maxlags=HAC_MAXLAGS) for data, formula, _ in specs],
        axis=1,
    )
    reg_df.columns = [dep for _, _, dep in specs]

    rows = [FOMC_M1, FOMC, FOMC_P1, INTERCEPT]
    reg_df = reorder_reg_output(reg_df, rows).drop(index="fe")

    # Label the estimation sample of each column, under the dependent variables.
    samples = (
        "{} & Full & Leads/lags & "
        f"{pd.Timestamp(SAMPLE_START):%Y}--{int(pd.Timestamp(SUBSAMPLE_SPLIT).year) - 1} & "
        f"{pd.Timestamp(SUBSAMPLE_SPLIT):%Y}-- & Ex 2008--09 & Full & Full \\\\"
    )

    latex_table = regression_table(
        reg_df,
        rows=rows,
        include_nobs=True,
        include_rsquared=True,
        include_fixed_effects=False,
        include_tabular=True,
        include_column_names=True,
        header_title="Dependent variable",
        header_subtitle=None,
        skip_cols=(),
        column_subheader=samples,
    )

    table_path = tab_dir / "fomc_premium.tex"
    with open(table_path, "w") as f:
        f.write(latex_table)
        f.write(_notes(df, stats))

    logging.info(f"Table saved to {table_path}")

    return reg_df
