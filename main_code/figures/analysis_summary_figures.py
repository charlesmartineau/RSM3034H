import logging
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def plot_news_trends(
    panel_df: pd.DataFrame, output_path: Path, plot_type: str = "regular"
) -> None:
    """
    Create time-series plot of news counts at monthly frequency.
    The bloomberg data starts in 2008-11, hence the plt.xlim from 2008 and ends in 2024-09-30.

    Args:
        panel_df: Panel dataset with news count columns
        output_path: Path to save the figure
        plot_type: Either "regular" for regular trading hours or "after_hours" for outside trading hours
    """
    # Convert date column to datetime if it's not already
    if "date" in panel_df.columns:
        panel_df["date"] = pd.to_datetime(panel_df["date"])
        panel_df["year_month"] = panel_df["date"].dt.to_period("M")
    else:
        logging.warning("No 'date' column found in panel dataset")
        return

    if plot_type == "regular":
        # Regular trading hours news counts

        monthly_panel = (
            panel_df.groupby(["permno", "year_month"])[
                ["blm_news_count", "rp_news_count"]
            ]
            .sum()
            .reset_index()
        )

        monthly_stats = (
            monthly_panel.groupby("year_month")
            .agg({"blm_news_count": "mean", "rp_news_count": "mean"})
            .reset_index()
        )

        # title = "Average Monthly News Counts (Regular Trading Hours)"
        blm_label = "Bloomberg"
        rp_label = "RavenPack"
        filename = "news_trends_regular.pdf"

    elif plot_type == "after_hours":
        # After-hours news counts (pre-open + post-close)
        panel_df["blm_after_hours"] = (
            panel_df["blm_news_count_post_close"] + panel_df["blm_news_count_pre_open"]
        )
        panel_df["rp_after_hours"] = (
            panel_df["rp_news_count_post_close"] + panel_df["rp_news_count_pre_open"]
        )
        # panel data is at the daily frequency.
        monthly_panel = (
            panel_df.groupby(["permno", "year_month"])[
                ["blm_after_hours", "rp_after_hours"]
            ]
            .sum()
            .reset_index()
        )

        monthly_stats = (
            monthly_panel.groupby("year_month")
            .agg({"blm_after_hours": "mean", "rp_after_hours": "mean"})
            .reset_index()
        )

        # title = "Average Monthly News Counts (After Hours)"
        blm_label = "Bloomberg (non-market hours)"
        rp_label = "RavenPack (non-market hours)"
        filename = "news_trends_after_hours.pdf"

    # Convert period back to datetime for plotting
    monthly_stats["date"] = monthly_stats["year_month"].dt.to_timestamp()
    # Create the plot

    LINEWIDTH = 2
    MARKERSIZE = 3

    fig, ax = plt.subplots(figsize=(8, 6))

    if plot_type == "regular":
        ax.plot(
            monthly_stats["date"],
            monthly_stats["blm_news_count"],
            label=blm_label,
            linewidth=LINEWIDTH,
            marker="o",
            markersize=MARKERSIZE,
        )
        ax.plot(
            monthly_stats["date"],
            monthly_stats["rp_news_count"],
            label=rp_label,
            linewidth=LINEWIDTH,
            marker="s",
            markersize=MARKERSIZE,
        )
    else:
        ax.plot(
            monthly_stats["date"],
            monthly_stats["blm_after_hours"],
            label=blm_label,
            linewidth=LINEWIDTH,
            marker="o",
            markersize=MARKERSIZE,
        )
        ax.plot(
            monthly_stats["date"],
            monthly_stats["rp_after_hours"],
            label=rp_label,
            linewidth=LINEWIDTH,
            marker="s",
            markersize=MARKERSIZE,
        )

    # ax.set_xlabel("Date")
    ax.set_ylabel("Average News Count", fontsize=14)
    ax.xaxis.set_tick_params(labelsize=12)
    ax.yaxis.set_tick_params(labelsize=12)
    # ax.set_title(title)
    ax.legend(frameon=False)
    ax.set_xlim([pd.to_datetime("2008-11-01"), pd.to_datetime("2024-09-01")])
    plt.tight_layout()

    # Save the figure
    output_file = output_path / filename
    plt.savefig(output_file, format="pdf", bbox_inches="tight")
    plt.close()

    logging.info(f"Saved {plot_type} news trends plot to {output_file}")


def plot_bloomberg_news_counts(panel_df: pd.DataFrame, output_path: Path) -> None:
    """
    Create time-series plot of Bloomberg news counts at monthly frequency.
    
    Args:
        panel_df: Panel dataset with Bloomberg news count columns
        output_path: Path to save the figure
    """
    # Convert date column to datetime if it's not already
    if "date" in panel_df.columns:
        panel_df["date"] = pd.to_datetime(panel_df["date"])
        panel_df["year_month"] = panel_df["date"].dt.to_period("M")
    else:
        logging.warning("No 'date' column found in panel dataset")
        return

    # Aggregate Bloomberg news counts by month
    monthly_panel = (
        panel_df.groupby(["permno", "year_month"])[
            ["blm_news_count", "blm_news_flash_count"]
        ]
        .sum()
        .reset_index()
    )

    monthly_stats = (
        monthly_panel.groupby("year_month")
        .agg({"blm_news_count": "mean", "blm_news_flash_count": "mean"})
        .reset_index()
    )

    # Convert period back to datetime for plotting
    monthly_stats["date"] = monthly_stats["year_month"].dt.to_timestamp()
    
    # Create the plot
    LINEWIDTH = 2
    MARKERSIZE = 3

    fig, ax = plt.subplots(figsize=(8, 6))

    ax.plot(
        monthly_stats["date"],
        monthly_stats["blm_news_count"],
        label="Bloomberg News",
        linewidth=LINEWIDTH,
        marker="o",
        markersize=MARKERSIZE,
    )
    ax.plot(
        monthly_stats["date"],
        monthly_stats["blm_news_flash_count"],
        label="Bloomberg News Flash",
        linewidth=LINEWIDTH,
        marker="s",
        markersize=MARKERSIZE,
    )

    ax.set_ylabel("Average News Count", fontsize=14)
    ax.xaxis.set_tick_params(labelsize=12)
    ax.yaxis.set_tick_params(labelsize=12)
    ax.legend(frameon=False)
    ax.set_xlim([pd.to_datetime("2008-11-01"), pd.to_datetime("2024-09-01")])
    plt.tight_layout()

    # Save the figure
    output_file = output_path / "bloomberg_news_counts.pdf"
    plt.savefig(output_file, format="pdf", bbox_inches="tight")
    plt.close()

    logging.info(f"Saved Bloomberg news counts plot to {output_file}")


def plot_ravenpack_news_counts(panel_df: pd.DataFrame, output_path: Path) -> None:
    """
    Create time-series plot of RavenPack news counts at monthly frequency.
    
    Args:
        panel_df: Panel dataset with RavenPack news count columns
        output_path: Path to save the figure
    """
    # Convert date column to datetime if it's not already
    if "date" in panel_df.columns:
        panel_df["date"] = pd.to_datetime(panel_df["date"])
        panel_df["year_month"] = panel_df["date"].dt.to_period("M")
    else:
        logging.warning("No 'date' column found in panel dataset")
        return

    rp_columns = [
        "rp_news_count_full_article",
        "rp_news_count_tabular",
        "rp_news_count_news_flash",
        "rp_news_count_press_release",
        "rp_news_count_sec",
    ]

    # Aggregate RavenPack news counts by month
    monthly_panel = (
        panel_df.groupby(["permno", "year_month"])[rp_columns]
        .sum()
        .reset_index()
    )

    monthly_stats = (
        monthly_panel.groupby("year_month")
        .agg({col: "mean" for col in rp_columns})
        .reset_index()
    )

    # Convert period back to datetime for plotting
    monthly_stats["date"] = monthly_stats["year_month"].dt.to_timestamp()
    
    # Create the plot
    LINEWIDTH = 2
    MARKERSIZE = 3

    fig, ax = plt.subplots(figsize=(12, 8))

    # Define markers for different lines
    markers = ["s", "^", "d", "v", "o"]
    
    # Define labels for better readability
    labels = [
        "Full Article",
        "Tabular",
        "News Flash",
        "Press Release",
        "SEC",
    ]

    for i, (col, label) in enumerate(zip(rp_columns, labels)):
        ax.plot(
            monthly_stats["date"],
            monthly_stats[col],
            label=f"RavenPack {label}",
            linewidth=LINEWIDTH,
            marker=markers[i % len(markers)],
            markersize=MARKERSIZE,
        )

    ax.set_ylabel("Average News Count", fontsize=14)
    ax.xaxis.set_tick_params(labelsize=12)
    ax.yaxis.set_tick_params(labelsize=12)
    ax.legend(frameon=False, bbox_to_anchor=(1.05, 1), loc='upper left')
    ax.set_xlim([pd.to_datetime("2008-11-01"), pd.to_datetime("2024-09-01")])
    plt.tight_layout()

    # Save the figure
    output_file = output_path / "ravenpack_news_counts.pdf"
    plt.savefig(output_file, format="pdf", bbox_inches="tight")
    plt.close()

    logging.info(f"Saved RavenPack news counts plot to {output_file}")


def create_analysis_summary_figures(panel_df: pd.DataFrame, fig_dir: Path) -> None:
    """
    Create all analysis summary figures.

    Args:
        panel_df: Panel dataset with news count columns
        fig_dir: Directory to save figures
    """
    logging.info("Creating analysis summary figures...")

    # Create regular trading hours news trends plot
    plot_news_trends(panel_df, fig_dir, plot_type="regular")

    # Create after-hours news trends plot
    plot_news_trends(panel_df, fig_dir, plot_type="after_hours")

    # Create Bloomberg news counts plot
    plot_bloomberg_news_counts(panel_df, fig_dir)

    # Create RavenPack news counts plot
    plot_ravenpack_news_counts(panel_df, fig_dir)

    logging.info("Analysis summary figures completed")
