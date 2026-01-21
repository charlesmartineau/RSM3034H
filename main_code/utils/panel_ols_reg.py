import logging

import pandas as pd
import statsmodels.formula.api as smf
from linearmodels import PanelOLS

PREFIX_MAP = {
    "neg_abn_ret": r"$1_{Ret^e<0}$",
    "abn_ret": r"$Ret^e$",
    "abs_abn_ret": r"$|Ret^e|$",
    "neg_ret": r"$1_{Ret<0}$",
    "ret": r"$Ret$",
    "abs_ret": r"$|Ret|$",
    "ea": r"$1_{EA}$",
    "ln_mcap": r"$ln(MCAP)$",
    "fomc": r"$1_{FOMC}$",
    "unemp": r"$1_{UNEMP}$",
    "n_analysts": r"N analysts",
    "ln_n_analysts": r"$ln(N analysts)$",
    "delta_vix": r"$\Delta VIX$",
    "mkt_rf": r"$Ret^M$",
    "day_mon": r"$1_{Mon}$",
    "day_tue": r"$1_{Tue}$",
    "day_wed": r"$1_{Wed}$",
    "day_thu": r"$1_{Thu}$",
    "day_fri": r"$1_{Fri}$",
    
}


def panel_ols(df, model):
    logging.info(f"Estimating model {model}...")

    reg = PanelOLS.from_formula(model, df).fit(
        cov_type="clustered", cluster_entity=True, cluster_time=True
    )

    fix_effects = reg.included_effects

    return pd.concat(
        [
            pd.DataFrame(
                {
                    f"{PREFIX_MAP[param]}_coef": reg.params[param],
                    f"{PREFIX_MAP[param]}_tstat": reg.tstats[param],
                    f"{PREFIX_MAP[param]}_bse": reg.std_errors[param],
                    f"{PREFIX_MAP[param]}_pval": reg.pvalues[param],
                },
                index=[0],
            ).T
            for param in reg.params.index
        ]
        + [
            pd.DataFrame(
                {
                    "rsquared": reg.rsquared,
                    "nobs": reg.nobs,
                    "fe": "Y" if fix_effects else "N",
                },
                index=[0],
            ).T
        ]
    )


def ols_reg(df: pd.DataFrame, formula: str) -> pd.DataFrame:
    """
    Run OLS regression and return coefficients with standard errors and p-values.

    Args:
        df: DataFrame with regression data
        formula: statsmodels formula (e.g., "y~1+x")

    Returns:
        DataFrame with coefficients, standard errors, t-stats, and p-values
    """
    reg = smf.ols(formula, data=df).fit(cov_type="HC1")

    output = []
    for param in reg.params.index:
        # Map parameter names to display names (capitalize vrp -> VRP)
        # Handle both "vrp" and "vrp_h1", "vrp_h3", etc.
        if param.startswith("vrp"):
            display_name = "VRP"
        else:
            display_name = param
        output.append(
            pd.DataFrame(
                {
                    f"{display_name}_coef": reg.params[param],
                    f"{display_name}_tstat": reg.tvalues[param],
                    f"{display_name}_bse": reg.bse[param],
                    f"{display_name}_pval": reg.pvalues[param],
                },
                index=[0],
            ).T
        )

    output.append(
        pd.DataFrame(
            {
                "rsquared": reg.rsquared,
                "nobs": int(reg.nobs),
            },
            index=[0],
        ).T
    )

    return pd.concat(output)
