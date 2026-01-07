from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def plot_n_stocks_per_year(panel: pd.DataFrame, fig_dir: Path) -> None:
    """
    Plot the number of unique firms (PERMNOs) per year.

    Parameters
    ----------
    panel : pd.DataFrame
        Panel dataset with daily frequency containing 'PERMNO' and 'date' columns
    fig_dir : Path
        Directory to save the figure
    """
    # Extract year from date
    panel_yearly = panel.copy()
    panel_yearly["year"] = panel_yearly["date"].dt.year

    # Count unique PERMNOs per year
    n_stocks = panel_yearly.groupby("year")["permno"].nunique().reset_index()
    n_stocks.columns = ["year", "n_stocks"]

    # Create the plot
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(n_stocks["year"], n_stocks["n_stocks"], linewidth=2, marker="o")
    ax.set_xlabel("Year")
    ax.set_ylabel("Number of Unique Firms")
    ax.set_title("Number of Unique Firms per Year")
    ax.grid(True, alpha=0.3)

    # Save the figure
    fig_path = fig_dir / "n_stocks_per_year.pdf"
    plt.tight_layout()
    plt.savefig(fig_path, bbox_inches="tight")
    plt.close()

    print(f"Figure saved to {fig_path}")
