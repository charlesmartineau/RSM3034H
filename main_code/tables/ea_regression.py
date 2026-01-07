from pathlib import Path

import pandas as pd

from ..utils import panel_ols
from .format import regression_table, reorder_reg_output


def create_ea_regression_table(panel: pd.DataFrame, tab_dir: Path) -> None:
    """
    Create regression table: regress excess returns (ret - rf) on EA dummy.

    Parameters
    ----------
    panel : pd.DataFrame
        Panel dataset with 'ret', 'rf', 'ea', 'permno', and 'date' columns
    tab_dir : Path
        Directory to save the table
    """
    # Prepare the data for panel regression
    # Set multi-index for panel data (entity, time)
    panel_reg = panel[["permno", "date", "ret", "mkt", "rf", "ea"]].copy()
    panel_reg["ret_rf"] = (panel_reg["ret"] - panel_reg["rf"]) 
    panel_reg["mkt_rf"] = (
        panel_reg["mkt"] - panel_reg["rf"] 
    )  # market excess return
    panel_reg = panel_reg.set_index(["permno", "date"])

    # Run the regression: ret - rf ~ ea
    models = [
        "ret_rf ~ ea",
        "ret_rf ~ ea + mkt_rf",
        "ret_rf ~ ea + mkt_rf + EntityEffects",
    ]

    reg_results = [panel_ols(panel_reg, model) for model in models]
    reg_df = pd.concat(reg_results, axis=1)

    # Reorder the output to have the correct format
    reg_df = reorder_reg_output(reg_df, [r"$1_{EA}$", "$Ret^M$"])

    # Generate LaTeX table
    latex_table = regression_table(
        reg_df,
        rows=[r"$1_{EA}$", "$Ret^M$"],
        include_nobs=True,
        include_rsquared=True,
        include_fixed_effects=True,
        include_tabular=True,
        include_column_names=False,
        header_title="Dependent variable: $Ret - R_f$ (\\%)",
        header_subtitle=None,
        skip_cols=(),
    )

    # Save the table
    table_path = tab_dir / "ea_regression.tex"
    with open(table_path, "w") as f:
        f.write(latex_table)

    print(f"Table saved to {table_path}")
