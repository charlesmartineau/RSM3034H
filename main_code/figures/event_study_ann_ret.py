from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats


def plot_event_study_earnings_ann_ret(event_df: pd.DataFrame, fig_dir: Path) -> None:
    """
    Create event study plots for earnings announcements showing BHAR.

    Parameters
    ----------
    panel : pd.DataFrame
        Panel dataset with columns: permno, date, ret, mkt, ea, sue, mcap_qnt
    fig_dir : Path
        Directory to save the figures
    """

    event_df = event_df[event_df["date"].dt.year >= 2010]
    # event_df = event_df[event_df["event_t"] >= 1]

    event_df["gret"] = 1 + event_df["ret"]
    event_df["gmkt"] = 1 + event_df["mkt"]
    event_df["gff_port"] = 1 + event_df["ff_port"]
    event_df["cumret"] = event_df.groupby(["permno", "ea_date"])["gret"].cumprod()
    event_df["cum_mkt"] = event_df.groupby(["permno", "ea_date"])["gmkt"].cumprod()
    event_df["cum_ff_port"] = event_df.groupby(["permno", "ea_date"])[
        "gff_port"
    ].cumprod()
    event_df["bhar"] = event_df["cumret"] - event_df["cum_ff_port"]

    # Plot 1: Average BHAR for small cap (mcap_qnt == 0)
    avg_bhar_small = (
        event_df[event_df["mcap_qnt"] == 0]
        .groupby("event_t")["bhar"]
        .mean()
        .reset_index()
    )
    avg_bhar_small = avg_bhar_small.sort_values("event_t")

    # Plot 1: BHAR by earnings announcement return quintile with 95% CI (small cap)
    def calc_stats(group):
        n = len(group)
        mean = group["bhar"].mean()
        se = group["bhar"].std() / np.sqrt(n)
        ci_95 = stats.t.ppf(0.975, n - 1) * se if n > 1 else 0
        return pd.Series({"mean_bhar": mean, "ci_95": ci_95, "n": n})

    bhar_by_quintile = (
        event_df[event_df["mcap_qnt"] == 0]
        .groupby(["ann_ret_qnt", "event_t"])
        .apply(calc_stats)
        .reset_index()
    )

    fig3, ax3 = plt.subplots(figsize=(12, 7))
    colors = plt.cm.RdYlGn(np.linspace(0.1, 0.9, 5))
    quintile_labels = [
        "Q1 (Negative Surprise)",
        "Q2",
        "Q3",
        "Q4",
        "Q5 (Positive Surprise)",
    ]

    for q in range(5):
        q_data = bhar_by_quintile[bhar_by_quintile["ann_ret_qnt"] == q].sort_values(
            "event_t"
        )
        ax3.plot(
            q_data["event_t"],
            q_data["mean_bhar"],
            color=colors[q],
            linewidth=1.5,
            label=quintile_labels[q],
        )
        ax3.fill_between(
            q_data["event_t"],
            q_data["mean_bhar"] - q_data["ci_95"],
            q_data["mean_bhar"] + q_data["ci_95"],
            color=colors[q],
            alpha=0.2,
        )

    ax3.axhline(y=0, color="gray", linestyle="--", linewidth=0.8)
    ax3.axvline(x=0, color="black", linestyle="--", linewidth=0.8)
    ax3.set_xlabel("Days Relative to Earnings Announcement")
    ax3.set_ylabel("Average Buy-and-Hold Abnormal Return (BHAR)")
    ax3.set_title("Average BHAR by Earnings Announcement Return Quintile (Small Cap)")
    ax3.legend(loc="upper left")
    ax3.grid(True, alpha=0.3)
    plt.tight_layout()
    fig3.savefig(
        fig_dir / "event_study_bhar_by_ann_ret_quintile_microcap.png",
        dpi=300,
        bbox_inches="tight",
    )
    plt.close(fig3)

    # Plot 2: BHAR by earnings surprise quintile with 95% CI (large cap)

    bhar_by_quintile = (
        event_df[event_df["mcap_qnt"] > 0]
        .groupby(["ann_ret_qnt", "event_t"])
        .apply(calc_stats)
        .reset_index()
    )

    fig3, ax3 = plt.subplots(figsize=(12, 7))
    colors = plt.cm.RdYlGn(np.linspace(0.1, 0.9, 5))
    quintile_labels = [
        "Q1 (Negative Surprise)",
        "Q2",
        "Q3",
        "Q4",
        "Q5 (Positive Surprise)",
    ]

    for q in range(5):
        q_data = bhar_by_quintile[bhar_by_quintile["ann_ret_qnt"] == q].sort_values(
            "event_t"
        )
        ax3.plot(
            q_data["event_t"],
            q_data["mean_bhar"],
            color=colors[q],
            linewidth=1.5,
            label=quintile_labels[q],
        )
        ax3.fill_between(
            q_data["event_t"],
            q_data["mean_bhar"] - q_data["ci_95"],
            q_data["mean_bhar"] + q_data["ci_95"],
            color=colors[q],
            alpha=0.2,
        )

    ax3.axhline(y=0, color="gray", linestyle="--", linewidth=0.8)
    ax3.axvline(x=0, color="black", linestyle="--", linewidth=0.8)
    ax3.set_xlabel("Days Relative to Earnings Announcement")
    ax3.set_ylabel("Average Buy-and-Hold Abnormal Return (BHAR)")
    ax3.set_title("Average BHAR by Earnings Announcement Return Quintile (Large Cap)")
    ax3.legend(loc="upper left")
    ax3.grid(True, alpha=0.3)
    plt.tight_layout()
    fig3.savefig(
        fig_dir / "event_study_bhar_by_ann_ret_quintile_large.png",
        dpi=300,
        bbox_inches="tight",
    )
    plt.close(fig3)
