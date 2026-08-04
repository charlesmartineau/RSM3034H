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
    # FOMC dummies in event time: -1 is the trading day before the announcement
    "fomc_m1": r"$1_{FOMC,-1}$",
    "fomc_p1": r"$1_{FOMC,+1}$",
    "vix": r"$VIX$",

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


def ols_reg_hac(df: pd.DataFrame, formula: str, maxlags: int = 5) -> pd.DataFrame:
    """
    Run a time-series OLS regression with Newey-West (HAC) standard errors.

    Daily return and volatility series are serially correlated and
    heteroskedastic, so plain OLS standard errors overstate precision. This is
    the time-series counterpart of :func:`ols_reg`, which uses HC1, and returns
    the same shape so the output can be passed straight to
    :func:`main_code.tables.format.regression_table`.

    Args:
        df: DataFrame with regression data, one row per date
        formula: statsmodels formula (e.g., "mkt_rf~1+fomc")
        maxlags: Number of Newey-West lags. Defaults to 5, i.e. one trading week.

    Returns:
        DataFrame with coefficients, standard errors, t-stats and p-values,
        indexed by the display names in ``PREFIX_MAP``.
    """
    logging.info(f"Estimating model {formula} with HAC({maxlags}) standard errors...")

    reg = smf.ols(formula, data=df).fit(
        cov_type="HAC", cov_kwds={"maxlags": maxlags}, use_t=False
    )

    output = [
        pd.DataFrame(
            {
                f"{PREFIX_MAP.get(param, param)}_coef": reg.params[param],
                f"{PREFIX_MAP.get(param, param)}_tstat": reg.tvalues[param],
                f"{PREFIX_MAP.get(param, param)}_bse": reg.bse[param],
                f"{PREFIX_MAP.get(param, param)}_pval": reg.pvalues[param],
            },
            index=[0],
        ).T
        for param in reg.params.index
    ]

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
