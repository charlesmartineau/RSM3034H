import logging
from pathlib import Path

import pandas as pd


def create_summary_stats_table(panel: pd.DataFrame, tab_dir: Path) -> None:
    """
    Create summary statistics table by market cap quintile.

    Args:
        panel: DataFrame containing the panel data
        tab_dir: Directory to save the table
    """
    logging.info("Creating summary statistics table by market cap quintile...")

    # Define the variables to analyze
    variables = ["blm_news_count", "blm_read_count", "rp_news_count"]

    # Define statistics to compute
    stats = ["mean", "25%", "50%", "75%"]

    # Filter out missing values and ensure mcap_qnt exists
    panel_clean = panel.dropna(subset=["mcap_qnt"])

    panel_clean = (
        panel_clean.groupby(["permno", "year_month"])[variables].sum().reset_index()
    )

    mcap_qnt = panel.groupby(["permno", "year_month"])["mcap_qnt"].first().reset_index()

    panel_clean = panel_clean.merge(mcap_qnt, on=["permno", "year_month"], how="left")

    # Group by market cap quintile and compute statistics
    summary_stats1 = panel_clean.groupby("mcap_qnt")[
        ["blm_news_count", "rp_news_count"]
    ].describe()
    summary_stats2 = (
        panel_clean[panel_clean["year_month"].dt.year >= 2015]
        .groupby("mcap_qnt")[["blm_read_count"]]
        .describe()
    )

    summary_stats = pd.concat(
        [summary_stats1, summary_stats2],
        axis=1,
    )

    # Select only the statistics we want
    summary_stats = summary_stats.loc[:, (slice(None), stats)]

    # Reshape the DataFrame to have variables and statistics as index
    summary_stats = summary_stats.T

    # Format the table for LaTeX output
    latex_table = format_summary_stats_table(summary_stats, variables, stats)

    # Save to LaTeX file
    with open(tab_dir / "summary_stats_table.tex", "w") as f:
        f.write(latex_table)

    logging.info(
        f"Summary statistics table saved to {tab_dir / 'summary_stats_table.tex'}"
    )


def format_summary_stats_table(
    summary_stats: pd.DataFrame, variables: list, stats: list
) -> str:
    """
    Format the summary statistics table for LaTeX output.

    Args:
        summary_stats: DataFrame with summary statistics
        variables: List of variable names
        stats: List of statistic names

    Returns:
        Formatted LaTeX table string
    """

    # Variable name mapping for LaTeX formatting
    var_map = {
        "blm_news_count": "\\textbf{Panel A.} Bloomberg news count",
        "blm_read_count": "\\textbf{Panel B.} Bloomberg read count",
        "rp_news_count": "\\textbf{Panel C.} Ravenpack news count",
    }

    # Statistics name mapping
    stats_map = {
        "mean": "Mean",
        "25%": "25th Pct",
        "50%": "Median",
        "75%": "75th Pct",
    }

    # Start building the LaTeX table
    n_quintiles = len(summary_stats.columns.unique())
    n_cols = n_quintiles + 1  # +1 for the variable names column

    latex = "\\begin{tabular}{l" + "c" * n_quintiles + "}\n"
    latex += "\\hline\\hline\n"

    # Header with quintile numbers
    quintile_labels = ["Q1 (small)", "Q2", "Q3", "Q4", "Q5 (large)"]
    latex += " & " + " & ".join(quintile_labels) + " \\\\\n"
    latex += "\\hline\n"

    # For each variable, add rows for each statistic
    for var in variables:
        var_display = var_map.get(var, var)
        latex += f"\\multicolumn{{{n_cols}}}{{c}}{{{var_display}}} \\\\\n"
        latex += "\\hline\n"

        for stat in stats:
            stat_display = stats_map.get(stat, stat)
            latex += f"\\quad {stat_display} & "

            # Get values for each quintile
            values = []
            for quintile in sorted(summary_stats.columns.unique()):
                value = summary_stats.loc[(var, stat), quintile]

                # Round to 0 decimal places
                rounded_value = round(value, 0)

                # Special case for zero
                if rounded_value == 0:
                    values.append("0")
                else:
                    values.append(f"{rounded_value:,.0f}")

            latex += " & ".join(values) + " \\\\\n"

        latex += "\\hline\n"
    latex += "\\hline\n"
    latex += "\\end{tabular}\n"

    return latex
