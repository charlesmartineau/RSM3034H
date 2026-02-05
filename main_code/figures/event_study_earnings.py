from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats


def plot_event_study_earnings(event_df: pd.DataFrame, fig_dir: Path) -> None:
    """
    Create event study plots for earnings announcements showing BHAR.

    Parameters
    ----------
    panel : pd.DataFrame
        Panel dataset with columns: permno, date, ret, mkt, ea, sue, mcap_qnt
    fig_dir : Path
        Directory to save the figures
    """
    
    event_df = event_df[event_df['date'].dt.year>=2020]
    event_df['gret'] = 1 + event_df['ret']
    event_df['gmkt'] = 1 + event_df['mkt']
    event_df['gff_port'] = 1 + event_df['ff_port']
    event_df['cumret'] = event_df.groupby(['permno', 'ea_date'])['gret'].cumprod()
    event_df['cum_mkt'] = event_df.groupby(['permno', 'ea_date'])['gmkt'].cumprod()
    event_df['cum_ff_port'] = event_df.groupby(['permno', 'ea_date'])['gff_port'].cumprod()
    event_df['bhar'] = event_df['cumret'] - event_df['cum_ff_port']

    # Plot 1: Average BHAR for small cap (mcap_qnt == 0)
    avg_bhar_small = (
        event_df[event_df["mcap_qnt"] == 0]
        .groupby("event_t")["bhar"]
        .mean()
        .reset_index()
    )
    avg_bhar_small = avg_bhar_small.sort_values("event_t")

    fig1, ax1 = plt.subplots(figsize=(10, 6))
    ax1.plot(
        avg_bhar_small["event_t"],
        avg_bhar_small["bhar"],
        marker="o",
        markersize=4,
        linewidth=1.5,
    )
    ax1.axhline(y=0, color="gray", linestyle="--", linewidth=0.8)
    ax1.axvline(
        x=0, color="red", linestyle="--", linewidth=0.8, label="Earnings Announcement"
    )
    ax1.set_xlabel("Days Relative to Earnings Announcement")
    ax1.set_ylabel("Average Buy-and-Hold Abnormal Return (BHAR)")
    ax1.set_title("Average BHAR Around Earnings Announcements (Small Cap)")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    plt.tight_layout()
    fig1.savefig(
        fig_dir / "event_study_bhar_small_cap.png", dpi=300, bbox_inches="tight"
    )
    plt.close(fig1)
    print(f"Figure saved to {fig_dir / 'event_study_bhar_small_cap.png'}")

    # Plot 2: Average BHAR for large cap (mcap_qnt > 0)
    avg_bhar_large = (
        event_df[event_df["mcap_qnt"] > 0]
        .groupby("event_t")["bhar"]
        .mean()
        .reset_index()
    )
    avg_bhar_large = avg_bhar_large.sort_values("event_t")

    fig2, ax2 = plt.subplots(figsize=(10, 6))
    ax2.plot(
        avg_bhar_large["event_t"],
        avg_bhar_large["bhar"],
        marker="o",
        markersize=4,
        linewidth=1.5,
    )
    ax2.axhline(y=0, color="gray", linestyle="--", linewidth=0.8)
    ax2.axvline(
        x=0, color="red", linestyle="--", linewidth=0.8, label="Earnings Announcement"
    )
    ax2.set_xlabel("Days Relative to Earnings Announcement")
    ax2.set_ylabel("Average Buy-and-Hold Abnormal Return (BHAR)")
    ax2.set_title("Average BHAR Around Earnings Announcements (Large Cap)")
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    plt.tight_layout()
    fig2.savefig(
        fig_dir / "event_study_bhar_large_cap.png", dpi=300, bbox_inches="tight"
    )
    plt.close(fig2)
    print(f"Figure saved to {fig_dir / 'event_study_bhar_large_cap.png'}")

    # Plot 3: BHAR by earnings surprise quintile with 95% CI (small cap)
    def calc_stats(group):
        n = len(group)
        mean = group["bhar"].mean()
        se = group["bhar"].std() / np.sqrt(n)
        ci_95 = stats.t.ppf(0.975, n - 1) * se if n > 1 else 0
        return pd.Series({"mean_bhar": mean, "ci_95": ci_95, "n": n})

    bhar_by_quintile = (
        event_df[event_df["mcap_qnt"] == 0]
        .groupby(["sue_qnt", "event_t"])
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
        q_data = bhar_by_quintile[bhar_by_quintile["sue_qnt"] == q].sort_values(
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
    ax3.set_title("Average BHAR by Earnings Surprise Quintile (Small Cap)")
    ax3.legend(loc="upper left")
    ax3.grid(True, alpha=0.3)
    plt.tight_layout()
    fig3.savefig(
        fig_dir / "event_study_bhar_by_surprise_quintile.png",
        dpi=300,
        bbox_inches="tight",
    )
    plt.close(fig3)
    print(f"Figure saved to {fig_dir / 'event_study_bhar_by_surprise_quintile.png'}")


    # Plot 3: BHAR by earnings surprise quintile with 95% CI (large cap)

    bhar_by_quintile = (
        event_df[event_df["mcap_qnt"] > 0]
        .groupby(["sue_qnt", "event_t"])
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
        q_data = bhar_by_quintile[bhar_by_quintile["sue_qnt"] == q].sort_values(
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
    ax3.set_title("Average BHAR by Earnings Surprise Quintile (Large Cap)")
    ax3.legend(loc="upper left")
    ax3.grid(True, alpha=0.3)
    plt.tight_layout()
    fig3.savefig(
        fig_dir / "event_study_bhar_by_surprise_quintile_large.png",
        dpi=300,
        bbox_inches="tight",
    )
    plt.close(fig3)
    print(f"Figure saved to {fig_dir / 'event_study_bhar_by_surprise_quintile_large.png'}")
