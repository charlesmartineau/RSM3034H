import logging

import pandas as pd
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
    "cum_ret_5d_m1": r"$Cum ret_{[-6,-1]}$",
    "cum_ret_20d_m6": r"$Cum ret_{[-25,-6]}$",
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
