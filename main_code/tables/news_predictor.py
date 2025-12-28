import logging
from pathlib import Path

import pandas as pd

from main_code.utils import PREFIX_MAP, panel_ols

from .format import regression_table, reorder_reg_output


def news_predictor_panel_reg_results(
    panel: pd.DataFrame, tab_dir: Path, savename: str, abn_ret: bool = True
) -> None:
    """
    Estimate panel regression models for news count prediction using PanelOLS.

    Args:
        panel_path: Path to panel data file
        tab_dir: Directory to save regression tables
    """
    logging.info("Loading panel data for news predictor regression...")

    # Sort by permno and date before creating forward-looking variables
    panel = panel.sort_values(["gsector", "date"]).reset_index(drop=True)

    # Create forward-looking variables (next day)
    panel["log_delta_blm_news_count_p1"] = panel.groupby("permno")[
        "log_delta_blm_news_count"
    ].shift(-1)
    panel["log_delta_rp_news_count_p1"] = panel.groupby("permno")[
        "log_delta_rp_news_count"
    ].shift(-1)

    # Set panel index
    panel["year_month"] = panel["date"] + pd.offsets.MonthEnd(0)

    panel = panel.set_index(["gsector", "year_month"])

    # Drop missing values for regression
    # panel = panel.dropna(
    #    subset=[
    #        "log_delta_blm_news_count",
    #        "log_delta_rp_news_count",
    #        "log_delta_blm_news_count_p1",
    #        "log_delta_rp_news_count_p1",
    #        "neg_abn_ret",
    #        "abn_ret",
    #        "abs_abn_ret",
    #       "ea",
    #    ]
    # )

    indep_model = {}
    indep_model[0] = "neg_abn_ret" if abn_ret else "neg_ret"
    indep_model[1] = "abn_ret + abs_abn_ret" if abn_ret else "ret+abs_ret"

    fe = "EntityEffects + TimeEffects"

    day_fe = "day_mon + day_tue + day_wed + day_thu + day_fri"

    ctrl = f"ea+ln_mcap+n_analysts+mkt_rf+{day_fe}"
    ctrl2 = f"ea+ln_mcap+n_analysts+mkt_rf+{day_fe}+cum_ret_5d_m1+cum_ret_20d_m6+fomc+unemp+delta_vix"

    est_models = {
        1: f"log_delta_blm_news_count~{indep_model[0]}+{ctrl}+{fe}",
        2: f"log_delta_blm_news_count~{indep_model[1]}+{ctrl}+{fe}",
        3: f"log_delta_blm_news_count~{indep_model[1]}+{ctrl2}+{fe}",
        4: f"log_delta_blm_news_count_p1~{indep_model[0]}+{ctrl}+{fe}",
        5: f"log_delta_blm_news_count_p1~{indep_model[1]}+{ctrl}+{fe}",
        6: f"log_delta_blm_news_count_p1~{indep_model[1]}+{ctrl2}+{fe}",
        7: f"log_delta_rp_news_count~{indep_model[0]}+{ctrl}+{fe}",
        8: f"log_delta_rp_news_count~{indep_model[1]}+{ctrl}+{fe}",
        9: f"log_delta_rp_news_count~{indep_model[1]}+{ctrl2}+{fe}",
        10: f"log_delta_rp_news_count_p1~{indep_model[0]}+{ctrl}+{fe}",
        11: f"log_delta_rp_news_count_p1~{indep_model[1]}+{ctrl}+{fe}",
        12: f"log_delta_rp_news_count_p1~{indep_model[1]}+{ctrl2}+{fe}",
    }

    reg_output = pd.concat(
        [panel_ols(panel, est_models[model]) for model in est_models], axis=1
    )

    logging.info("All models estimated. Creating LaTeX tables...")

    reg_output.columns = [
        "BLM$_t$",
        "BLM$_t$",
        "BLM$_t$",
        "BLM$_{t+1}$",
        "BLM$_{t+1}$",
        "BLM$_{t+1}$",
        "RP$_t$",
        "RP$_t$",
        "RP$_t$",
        "RP$_{t+1}$",
        "RP$_{t+1}$",
        "RP$_{t+1}$",
    ]
    # regression of SUE on sentiment from stocktwits
    # indep_var = [r"$1_{Ret^e<0}$", r"$Ret^e$", r"$|Ret^e|$", r"$1_{EA}$", r"$ln(MCAP)$"]

    # Set the order of independent variables to be displayed in the table
    if abn_ret:
        indep_var = [
            "neg_abn_ret",
            "abn_ret",
            "abs_abn_ret",
            "ea",
            "ln_mcap",
            "n_analysts",
            "mkt_rf",
            "cum_ret_5d_m1",
            "cum_ret_20d_m6",
            "fomc",
            "unemp",
            "delta_vix",
        ]
    else:
        indep_var = [
            "neg_ret",
            "ret",
            "abs_ret",
            "ea",
            "ln_mcap",
            "n_analysts",
            "mkt_rf",
            "cum_ret_5d_m1",
            "cum_ret_20d_m6",
            "fomc",
            "unemp",
            "delta_vix",
        ]

    # Retrieve the LaTeX formatted names for independent variables
    indep_var_latex = [PREFIX_MAP.get(var, var) for var in indep_var]

    # Reorder the regression output DataFrame
    reg_table = reorder_reg_output(reg_output, indep_var_latex)

    with open(tab_dir / f"{savename}.tex", "w") as f:
        f.write(
            regression_table(
                reg_table,
                rows=indep_var_latex,
                include_column_names=True,
                include_fixed_effects=True,
                header_subtitle="\cmidrule(lr){2-7} \cmidrule(lr){8-13} \n",
                header_title="Dependent var.: $\Delta$ Log(News count)$_t$",
            )
        )


def news_predictor_panel_reg(
    panel: pd.DataFrame, tab_dir: Path, abn_ret: bool = True
) -> None:
    """
    Run news predictor regression on the provided panel data and save results.

    Args:
        panel: DataFrame containing the panel data
        tab_dir: Directory to save regression tables
        savename: Name for the saved regression table file
    """

    # ABNORMAL RETURN REGRESSIONS
    if abn_ret:
        logging.info("Running news predictor regression...")
        news_predictor_panel_reg_results(panel, tab_dir, "news_predictor_results")

        logging.info("Running news predictor regression for large mcap...")
        news_predictor_panel_reg_results(
            panel[panel["mcap_qnt"] > 2], tab_dir, "news_predictor_large_stocks_results"
        )

        logging.info("Running news predictor regression for small mcap...")
        news_predictor_panel_reg_results(
            panel[panel["mcap_qnt"] <= 2],
            tab_dir,
            "news_predictor_small_stocks_results",
        )

    else:
        # RAW RETURN REGRESSIONS
        logging.info("Running news predictor regression with raw return...")
        news_predictor_panel_reg_results(
            panel, tab_dir, "news_predictor_raw_ret_results", abn_ret=False
        )

        logging.info(
            "Running news predictor regression for large mcap with raw return..."
        )
        news_predictor_panel_reg_results(
            panel[panel["mcap_qnt"] > 2],
            tab_dir,
            "news_predictor_large_stocks_raw_ret_results",
            abn_ret=False,
        )

        logging.info(
            "Running news predictor regression for small mcap with raw return..."
        )
        news_predictor_panel_reg_results(
            panel[panel["mcap_qnt"] <= 2],
            tab_dir,
            "news_predictor_small_stocks_raw_ret_results",
            abn_ret=False,
        )
