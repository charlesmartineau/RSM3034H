from typing import Iterable, Optional, Union

import numpy as np
import pandas as pd


def reorder_reg_output(df, indep_var):
    indep_var_stat = ["coef", "tstat", "bse", "pval"]
    reorder_var = [f"{i}_{j}" for i in indep_var for j in indep_var_stat] + [
        "rsquared",
        "nobs",
        "fe",
    ]
    return df.reindex(reorder_var)


def stars(pval: float) -> str:
    if pval < 0.01:
        return "***"
    elif pval < 0.05:
        return "**"
    elif pval < 0.1:
        return "*"
    else:
        return ""


def format_coef(coef: float, pval: float, decimal: int = 3) -> str:
    return "" if np.isnan(coef) else f"{coef:0.{decimal}f}{stars(pval)}"


def format_bse(bse: float) -> str:
    return "" if np.isnan(bse) else f"({bse:0.3f})"


def format_rsquared(rsquared: float) -> str:
    return f"{rsquared:0.2f}"


def format_nobs(nobs: Union[int, float]) -> str:
    return f"{nobs:,.0f}"


def format_pct_decimal(pct: Union[int, float], decimal: int = 2) -> str:
    return f"{pct:.{decimal}f}"


def format_pct_no_decimal(pct: Union[int, float]) -> str:
    return f"{pct:.0f}"


def format_tstat_decimal(pct: Union[int, float]) -> str:
    return f"[{pct:.2f}]"


def regression_table_header(
    reg: pd.DataFrame,
    n_cols: int,
    include_tabular: bool = True,
    include_column_names: bool = True,
    header_title: Optional[str] = "Dependent variable",
    header_subtitle: Optional[str] = None,
    skip_cols: Iterable[str] = (),
) -> str:
    header = "\\begin{tabular}{r" + ("c" * n_cols) + "}\n" if include_tabular else ""
    if header_title is not None:
        header += (
            "\\hline\\hline\n{} & \\multicolumn{"
            + str(n_cols)
            + "}{c}{"
            + header_title
            + "} \\\\\n"
        )
    else:
        header += "\\hline\\hline\n"
    # Count number of columns with same name. Assumes duplicates are adjacent.
    if header_subtitle is not None:
        header += header_subtitle + "\n"
    col_names_cnt = []
    for i, col in enumerate(reg.columns):
        if i in skip_cols:
            col_names_cnt.append(["", 1])
        elif col_names_cnt and (col == col_names_cnt[-1][0]):
            col_names_cnt[-1][1] += 1
        else:
            col_names_cnt.append([col, 1])
    format_multicolumn = lambda col, cnt: (
        col if cnt == 1 else "\multicolumn{" + str(cnt) + "}{c}{" + col + "}"
    )
    if include_column_names:
        header += (
            " & ".join(
                ["{}"] + [format_multicolumn(col, cnt) for col, cnt in col_names_cnt]
            )
            + "\\\\\n"
        )
    header += (
        " & ".join(
            (
                ["{}"]
                + [
                    (f"({i + 1})" if i not in skip_cols else "")
                    for i, _ in enumerate(reg.columns)
                ]
            )
        )
        + "\\\\\n"
    )
    midrule_cnt = 1
    for col, cnt in col_names_cnt:
        if col != "":
            header += "  " * cnt
            header += (
                "\cmidrule(lr){"
                + str(midrule_cnt + 1)
                + "-"
                + str(midrule_cnt + cnt)
                + "}"
            )
        midrule_cnt += cnt
    header += "\n"
    return header


def regression_table_body(
    reg: pd.DataFrame,
    rows: Iterable[str],
    skip_cols: Iterable[str] = (),
) -> str:
    body = ""
    for row in rows:
        body += row + " & "
        body += (
            " & ".join(
                [
                    (
                        format_coef(
                            reg.iloc[:, i][f"{row}_coef"],
                            reg.iloc[:, i][f"{row}_pval"],
                        )
                        if i not in skip_cols
                        else ""
                    )
                    for i, _ in enumerate(reg.columns)
                ]
            )
            + "\\\\\n & "
        )
        body += (
            " & ".join(
                [
                    (
                        format_bse(reg.iloc[:, i][f"{row}_bse"])
                        if i not in skip_cols
                        else ""
                    )
                    for i, _ in enumerate(reg.columns)
                ]
            )
            + "\\\\\n"
        )
    return body


def regression_table_footer(
    reg: pd.DataFrame,
    include_nobs: bool = True,
    include_rsquared: bool = True,
    include_fixed_effects: bool = False,
    include_time_effects_only: bool = False,
    include_tabular: bool = True,
    skip_cols: Iterable[str] = (),
) -> str:
    table = "\\midrule \\ \n"
    if include_nobs:
        table += (
            "$N$ & "
            + " & ".join(
                [
                    (format_nobs(reg.iloc[:, i]["nobs"]) if i not in skip_cols else "")
                    for i, _ in enumerate(reg.columns)
                ]
            )
            + "\\\\\n"
        )
    if include_rsquared:
        table += (
            "$R^2(\%)$ & "
            + " & ".join(
                [
                    (
                        format_rsquared(reg.iloc[:, i]["rsquared"] * 100)
                        if i not in skip_cols
                        else ""
                    )
                    for i, _ in enumerate(reg.columns)
                ]
            )
            + "\\\\\n"
        )
    if include_fixed_effects:
        if include_time_effects_only:
            fe_name = "Date FE"
        if include_fixed_effects and not include_time_effects_only:
            fe_name = "Firm FE"
        else:
            fe_name = "Firm \& Yr-mth FE"
        table += (
            f"{fe_name} & "
            + " & ".join(
                [
                    (reg.iloc[:, i]["fe"] if i not in skip_cols else "")
                    for i, _ in enumerate(reg.columns)
                ]
            )
            + "\\\\\n"
        )
    table += "\\hline\\hline\n"
    table += "\\end{tabular}\n" if include_tabular else ""
    return table


def regression_table(
    reg: pd.DataFrame,
    rows: Iterable[str],
    include_nobs: bool = True,
    include_rsquared: bool = True,
    include_fixed_effects: bool = False,
    include_tabular: bool = True,
    include_column_names: bool = True,
    header_title: Optional[str] = "Dependent variable",
    header_subtitle: Optional[str] = None,
    skip_cols: Iterable[str] = (),
) -> str:
    n_cols = reg.shape[1]
    print(include_tabular)
    return (
        regression_table_header(
            reg,
            n_cols,
            include_tabular,
            include_column_names,
            header_title,
            header_subtitle,
            skip_cols,
        )
        + regression_table_body(reg, rows, skip_cols)
        + regression_table_footer(
            reg,
            include_nobs,
            include_rsquared,
            include_fixed_effects,
            skip_cols,
        )
    )
