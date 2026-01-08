from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def plot_n_earnings_per_year(panel: pd.DataFrame, fig_dir: Path) -> None:
    """
    Plot the number of earnings announcements per year.

    Parameters
    ----------
    panel : pd.DataFrame
        Panel dataset with daily frequency containing earnings announcement data
    fig_dir : Path
        Directory to save the figure
    """
    # Filter to rows that have earnings announcements
    # Assuming earnings announcements are identified by non-null 'sue' column
    ea_data = panel[panel["ea"].notna()].copy()

    # Extract year from date
    ea_data["year"] = ea_data["date"].dt.year

    # Count number of earnings announcements per year
    n_earnings = ea_data.groupby("year").size().reset_index()
    n_earnings.columns = ["year", "n_earnings"]

    # Create the plot
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(n_earnings["year"], n_earnings["n_earnings"], linewidth=2, marker="o")
    ax.set_xlabel("Year")
    ax.set_ylabel("Number of Earnings Announcements")
    ax.set_title("Number of Earnings Announcements per Year")
    ax.grid(True, alpha=0.3)

    # Save the figure
    fig_path = fig_dir / "n_earnings_per_year.pdf"
    plt.tight_layout()
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()

    print(f"Figure saved to {fig_path}")
