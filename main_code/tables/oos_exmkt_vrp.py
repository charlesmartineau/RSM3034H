from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from .format import regression_table

from ..utils import ols_reg
from ..utils.files import get_latest_file


def insample_regression(df: pd.DataFrame, indep_var: str, tab_dir: Path, savename: str):

    df_sub = df[df[indep_var].notnull()]
    # put market return in %
    for var in ["exmkt_h1", "exmkt_h3", "exmkt_h6", "exmkt_h12"]:
        df_sub[var] = df_sub[var] * 100

    reg_output = pd.concat(
        [
            ols_reg(df_sub[df_sub["exmkt_h1"].notnull()], f"exmkt_h1~1+{indep_var}"),
            ols_reg(df_sub[df_sub["exmkt_h3"].notnull()], f"exmkt_h3~1+{indep_var}"),
            ols_reg(df_sub[df_sub["exmkt_h6"].notnull()], f"exmkt_h6~1+{indep_var}"),
            ols_reg(df_sub[df_sub["exmkt_h12"].notnull()], f"exmkt_h12~1+{indep_var}"),
        ],
        axis=1,
    )

    reg_output.columns = ["h=1", "h=3", "h=6", "h=12"]

    with open(tab_dir / f"{savename}.tex", "w") as f:
        f.write(
            regression_table(
                reg_output,
                rows=["VRP", "Intercept"],
                header_title="Dep. var.: Excess Market Ret$_{t+h}$ (\%)",
                include_column_names=True,
                include_fixed_effects=False,
            )
        )

    return reg_output


def outofsample_regression(
    df_dict: dict, indep_var: str, tab_dir: Path, savename: str, pre_2020: bool = False
):
    reg_output = []
    for h in df_dict:
        df = df_dict[h].copy()
        if pre_2020:
            df = df[:"2019-12-31"]

        reg_output.append(
            ols_reg(df[df[f"exmkt_h{h}"].notnull()], f"exmkt_h{h}~1+{indep_var}_h{h}")
        )

    reg_output = pd.concat(reg_output, axis=1)

    reg_output.columns = ["h=1", "h=3", "h=6", "h=12"]

    with open(tab_dir / f"{savename}.tex", "w") as f:
        f.write(
            regression_table(
                reg_output,
                rows=["VRP", "Intercept"],
                header_title="Dep. var.: Excess Market Ret$_{t+h}$",
                include_column_names=True,
                include_fixed_effects=False,
            )
        )
    return reg_output


def get_individual_predictor_oos_forecast(
    df,
    dep_var,
    indep_var,
    start_date_oos="1999-11-30",
    horizon="1",
):
    """
    This function computes the out-of-sample forecast for a given horizon and predictor

    Args:
        df (pd.dataframe): panel data
        dep_var (_type_): The variable to be forecasted
        indep_var (_type_): The predictor
        start_date_oos (_type_): _description_
        horizon (str, optional): _description_. Defaults to "1".

    Returns:
        time-series of the out-of-sample forecast
    """
    pred = df[["date", dep_var, indep_var]].dropna()
    output = []
    # select the starting oos sample
    dates = pred[pred["date"] >= start_date_oos]["date"]
    for dt in dates:
        pred_ = pred[pred["date"] <= dt]
        reg = smf.ols(dep_var + "~" + indep_var, data=pred_).fit()
        res_out = pd.DataFrame(
            data={
                "date": dt,
                "pred_loading": reg.params[indep_var],
                "intercept": reg.params["Intercept"],
            },
            index=[0],
        )
        output.append(res_out)
    output = pd.concat(output)
    output.index = range(len(output))
    output = output.merge(df[["exmkt", dep_var, indep_var, "date"]], on="date")
    # lag the intercept and pred coefficient to construct the oos-forecast
    output["intercept"] = output["intercept"].shift()
    output["pred_loading"] = output["pred_loading"].shift()

    output[f"{indep_var}_h{horizon}"] = (
        output["intercept"] + output["pred_loading"] * output[indep_var]
    )
    # remove the first entry as it is only NaN
    oos_output = output[1:]

    return oos_output.set_index("date")


# compute the oos-R2
def oos_r2_with_stars(oos_r2_, tval: float) -> str:
    if tval < 1.282:
        return "{:.3f}".format(oos_r2_)
    elif (tval >= 1.282) & (tval < 1.645):
        return "{:.3f}".format(oos_r2_) + "$^{*}$"
    elif (tval >= 1.645) & (tval < 1.96):
        return "{:.3f}".format(oos_r2_) + "$^{**}$"
    else:
        return "{:.3f}".format(oos_r2_) + "$^{***}$"


def compute_exmkt_oos_r2(vrp_for, df, restriction=False):
    """
    Computes the out-of-sample R-squared for the given exogenous market variable.

    Calculates the mean squared forecast error (msfe) and mean squared historical error (msfe_hist)
    for the out-of-sample predictions and historical values.

    The out-of-sample R-squared is computed as 1 - msfe / msfe_hist.

    Statistical significance is determined by a Clark-West test.

    Args:
    df_oos: DataFrame containing out-of-sample predictions and historical values
    restriction: Whether to apply out-of-sample restriction (default False)

    Returns:
    oos_r2_exmkt: List of out-of-sample R-squared values with stars indicating significance

    """
    oos_r2_exmkt = []
    diff_sse_vrp = []
    for h in [1, 3, 6, 12]:
        df_oos = (
            vrp_for[h].reset_index().merge(df[["date", f"hist_exmkt_h{h}"]], on="date")
        )
        if restriction:  # add the restriction
            print("Add OOS restriction that OOS is positive")
            df_oos.loc[df_oos[f"vrp_h{h}"] < 0, f"vrp_h{h}"] = 0

        df_oos["msfe"] = (df_oos[f"exmkt_h{h}"] - df_oos[f"vrp_h{h}"]) ** 2
        df_oos["msfe_hist"] = (df_oos[f"exmkt_h{h}"] - df_oos[f"hist_exmkt_h{h}"]) ** 2
        df_oos["hist_minus_pred"] = (
            df_oos[f"hist_exmkt_h{h}"] - df_oos[f"vrp_h{h}"]
        ) ** 2
        # add the significance of the OOS-R2
        df_oos["cw_fstat"] = df_oos["msfe_hist"] - (
            df_oos["msfe"] - df_oos["hist_minus_pred"]
        )

        df_oos[f"diff_sse_vrp_h{h}"] = (
            df_oos["msfe_hist"].cumsum() - df_oos["msfe"].cumsum()
        )
        df_oos = df_oos.set_index("date")
        diff_sse_vrp.append(df_oos[f"diff_sse_vrp_h{h}"])

        reg = smf.ols("cw_fstat~1", data=df_oos).fit()
        tval = reg.tvalues["Intercept"]

        oos_r2_val = 1 - df_oos["msfe"].sum() / df_oos["msfe_hist"].sum()
        oos_r2_exmkt.append(oos_r2_with_stars(oos_r2_val, tval))

    diff_sse_vrp = pd.concat(diff_sse_vrp, axis=1)

    return [oos_r2_exmkt, diff_sse_vrp]


def plot_diff_sse(diff_sse: pd.DataFrame, fig_dir: Path, savename: str) -> None:
    """
    Plot the cumulative difference in sum of squared errors for all horizons.

    Args:
        diff_sse: DataFrame with columns diff_sse_vrp_h1, diff_sse_vrp_h3, etc.
        fig_dir: Directory to save the figure
        savename: Filename for the saved figure (without extension)
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    horizon_labels = {
        "diff_sse_vrp_h1": "h=1",
        "diff_sse_vrp_h3": "h=3",
        "diff_sse_vrp_h6": "h=6",
        "diff_sse_vrp_h12": "h=12",
    }

    for col in diff_sse.columns:
        ax.plot(diff_sse.index, diff_sse[col], label=horizon_labels.get(col, col))

    ax.axhline(y=0, color="black", linestyle="--", linewidth=0.8)
    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative $\\Delta$ SSE (Historical - VRP)")
    ax.legend()
    ax.grid(True, alpha=0.3)

    fig_path = fig_dir / f"{savename}.png"
    plt.tight_layout()
    plt.savefig(fig_path, dpi=150, bbox_inches="tight")
    plt.close()

    print(f"Figure saved to {fig_path}")


def load_vrp(download_dir: Path) -> pd.DataFrame:
    """
    Load VRP data from Hao Zhou's website https://sites.google.com/site/haozhouspersonalhomepage/
    Data available until 2023. Use the function from download_data.py to download the vrp data.

    Args:
        download_dir (Path): download cache directory

    Returns:
        pd.DataFrame: time-series of VRP
    """
    vrp_file = get_latest_file(download_dir / "vrp_monthly.parquet")
    vrp = pd.read_parquet(vrp_file)
    return vrp[["date", "vrp"]]


def oos_regression_example(download_dir: Path, tab_dir: Path, fig_dir: Path):
    # load fama french factors for the market return and risk free rate
    ff_file = get_latest_file(download_dir / "ff5_monthly.parquet")
    ff = pd.read_parquet(ff_file)

    # compute market return as mkt_rf + rf
    ff["mkt"] = ff["mkt_rf"] + ff["rf"]

    # load the predictor vrp
    vrp = load_vrp(download_dir)

    # merge
    df = pd.merge(ff[["date", "mkt", "rf"]], vrp, on="date", how="left")
    df["exmkt"] = df["mkt"] - df["rf"]
    # h=1
    df["exmkt_h1"] = df["exmkt"].shift(-1)

    # create log returns to compute total 3, 6, 12 months ahead returns
    df["ln_mkt"] = np.log(1 + df["mkt"])
    df["ln_rf"] = np.log(1 + df["rf"])

    # returns at different horizons (for 3, 6, 12 months)
    for h in [3, 6, 12]:
        df[f"ln_mkt_h{h}"] = df["ln_mkt"].rolling(h, min_periods=h).sum()
        df[f"ln_rf_h{h}"] = df["ln_rf"].rolling(h, min_periods=h).sum()
        df[f"mkt_h{h}"] = np.exp(df[f"ln_mkt_h{h}"]) - 1
        df[f"rf_h{h}"] = np.exp(df[f"ln_rf_h{h}"]) - 1
        df[f"exmkt_h{h}"] = df[f"mkt_h{h}"] - df[f"rf_h{h}"]
        df[f"exmkt_h{h}"] = df[f"exmkt_h{h}"].shift(-h)
        df = df.drop(columns=[f"ln_mkt_h{h}", f"ln_rf_h{h}", f"mkt_h{h}", f"rf_h{h}"])

    # Compute historical average of exmkt
    for h in [1, 3, 6, 12]:
        df[f"hist_exmkt_h{h}"] = df[f"exmkt_h{h}"].expanding().mean().shift()

    # End data in 2023
    df = df[df["date"] <= "2023-12-31"]

    # Insample regression
    is_reg = insample_regression(df, "vrp", tab_dir, "reg_insample_exmkt_vrp")
    is_reg = insample_regression(
        df[df["date"] <= "2019-12-31"], "vrp", tab_dir, "reg_insample_exmkt_vrp_pre2020"
    )

    vrp_oos = {
        h: get_individual_predictor_oos_forecast(
            df=df,
            dep_var=f"exmkt_h{h}",
            indep_var="vrp",
            start_date_oos="1999-11-30",
            horizon=str(h),
        )
        for h in [1, 3, 6, 12]
    }

    outofsample_regression(vrp_oos, "vrp", tab_dir, "reg_outofsample_exmkt_vrp")
    outofsample_regression(
        vrp_oos, "vrp", tab_dir, "reg_outofsample_exmkt_vrp_pre2020", pre_2020=True
    )

    oos_tab = pd.concat(
        [
            pd.DataFrame(compute_exmkt_oos_r2(vrp_oos, df, restriction=False)[0]).T,
            pd.DataFrame(compute_exmkt_oos_r2(vrp_oos, df, restriction=True)[0]).T,
        ]
    )

    oos_tab.columns = ["h=1", "h=3", "h=6", "h=12"]
    oos_tab.index = ["No restriction", "Restriction: $E_t[r_{M,t+h}]>0$"]

    oos_tab.to_latex(tab_dir / "oos_r2_exmkt_vrp.tex", escape=False)

    # cumulative difference in sum of squared errors - plot figures
    diff_sse_no_restriction = compute_exmkt_oos_r2(vrp_oos, df, restriction=False)[1]
    plot_diff_sse(diff_sse_no_restriction, fig_dir, "diff_sse_vrp_no_restriction")

    diff_sse_with_restriction = compute_exmkt_oos_r2(vrp_oos, df, restriction=True)[1]
    plot_diff_sse(diff_sse_with_restriction, fig_dir, "diff_sse_vrp_with_restriction")
