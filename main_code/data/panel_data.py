# %%
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

from ..utils import get_latest_file

load_dotenv()


CRSP_START_DATE = "2008-01-01"
CRSP_END_DATE = "2024-12-31"


# load crsp file
def load_crsp_file(path: Path) -> pd.DataFrame:
    crsp = pd.read_parquet(get_latest_file(path / "crsp_daily.parquet"))
    crsp = crsp[crsp["date"] >= CRSP_START_DATE]  # filter for dates after 2007-01-01
    crsp["year_month"] = crsp["date"].dt.to_period("M")
    crsp = crsp.rename(columns={"ncusip": "cusip"})

    # merge on permno and select only the dates where the link is valid
    link_tab = pd.read_parquet(
        get_latest_file(path / "crsp_compu_link_table.parquet")
    ).rename(columns={"lpermno": "permno"})
    link_tab = link_tab[["gvkey", "permno", "linkdt", "linkenddt"]]
    link_tab["linkenddt"] = link_tab["linkenddt"].fillna(pd.to_datetime(CRSP_END_DATE))
    crsp = crsp.merge(link_tab, on="permno", how="left")
    crsp = crsp[crsp["date"].between(crsp["linkdt"], crsp["linkenddt"])]
    crsp = crsp.drop(columns=["linkdt", "linkenddt"])
    # drop_duplicates
    crsp = crsp.drop_duplicates(subset=["permno", "date"])

    return crsp


def load_fama_french_returns_data(df: pd.DataFrame, path: Path) -> pd.DataFrame:
    ff = pd.read_parquet(get_latest_file(path / "ff5.parquet"))
    ff["date"] = pd.to_datetime(ff["date"])
    ff["mkt"] = ff["mkt_rf"] + ff["rf"]

    return df.merge(ff, on="date", how="left")


def load_fama_french_me_breakpoints(df: pd.DataFrame, path: Path) -> pd.DataFrame:
    ff_me = pd.read_parquet(get_latest_file(path / "ff_size_breakpoints.parquet"))
    # keep only the 20th percentile cuts
    ff_me = ff_me[["date", "size_bp4", "size_bp8", "size_bp12", "size_bp16"]].rename(
        columns={
            "size_bp4": "ff_me_20",
            "size_bp8": "ff_me_40",
            "size_bp12": "ff_me_60",
            "size_bp16": "ff_me_80",
        }
    )

    ff_me["year_month"] = ff_me["date"].dt.to_period("M")

    return df.merge(ff_me.drop(columns="date"), on=["year_month"], how="left")


def load_ibes_data(df: pd.DataFrame, path: Path) -> pd.DataFrame:
    ibes = pd.read_parquet(path / "ibes/ibes_sue.parquet")
    ibes = ibes[ibes["datetime"] >= "2008-01-01"]  # filter for dates after 2007-01-01
    ibes = ibes[ibes["datetime"] <= "2024-12-31"]  # filter for dates after 2007-01-01
    ibes["ea_date"] = pd.to_datetime(ibes["datetime"].dt.date)

    # check if the time in ibes['datetime'] is after 4pm, if so, set it to the next day
    ibes["ea_date_adj"] = ibes["datetime"].apply(
        lambda x: x + pd.Timedelta(days=1) if x.hour >= 16 else x
    )
    # convert to date
    ibes["ea_date_adj"] = pd.to_datetime(ibes["ea_date_adj"].dt.date)

    # check if the column "date" in ibes is in crsp_dates, it not, take the next date in crsp_dates
    crsp_dates = df[df["date"].dt.dayofweek < 5]["date"].unique()
    # remove weekends from crsp_dates
    crsp_dates = pd.to_datetime(crsp_dates)
    ibes["ea_date_adj"] = ibes["ea_date_adj"].apply(
        lambda x: crsp_dates[crsp_dates >= x][0]
    )
    ibes_ = ibes[["permno", "ea_date_adj", "sue"]].copy()
    ibes_["ea"] = 1
    # there about 100 dups (dual shares related to the same permno and date)
    ibes_ = ibes_.drop_duplicates(subset=["permno", "ea_date_adj"])
    ibes_ = ibes_.rename(columns={"ea_date_adj": "date"})

    return df.merge(ibes_, on=["permno", "date"], how="left")


def load_ibes_analyst_coverage_data(df: pd.DataFrame, path: Path) -> pd.DataFrame:
    """
    Loads the IBES analyst coverage data.
    """
    ibes = pd.read_parquet(path / "ibes/ibes_sue.parquet")
    ibes = ibes[ibes["datetime"] >= "2008-01-01"]  # filter for dates after 2007-01-01
    ibes = ibes[["permno", "datetime", "numest"]]
    ibes = ibes.rename(columns={"numest": "n_analysts"})
    ibes["year_quarter"] = ibes["datetime"].dt.to_period("Q")
    ibes = ibes[["year_quarter", "permno", "n_analysts"]].drop_duplicates()
    ibes = ibes.groupby(["year_quarter", "permno"]).first().reset_index()

    df["year_quarter"] = df["date"].dt.to_period("Q")

    df = df.merge(ibes, on=["year_quarter", "permno"], how="left").drop(
        columns=["year_quarter"]
    )

    df["n_analysts"] = df["n_analysts"].fillna(0)
    df["ln_n_analysts"] = np.log(df["n_analysts"] + 1)

    return df


def assign_mcap_breakpoints(df: pd.DataFrame) -> pd.DataFrame:
    # assign the mcap quintiles based on the ff_me_20, ff_me_40, ff_me_60, ff_me_80
    df["mcap_qnt"] = np.nan
    df.loc[df["mcap"] < df["ff_me_20"], "mcap_qnt"] = 0
    df.loc[
        (df["mcap"] >= df["ff_me_20"]) & (df["mcap"] < df["ff_me_40"]),
        "mcap_qnt",
    ] = 1
    df.loc[
        (df["mcap"] >= df["ff_me_40"]) & (df["mcap"] < df["ff_me_60"]),
        "mcap_qnt",
    ] = 2
    df.loc[
        (df["mcap"] >= df["ff_me_60"]) & (df["mcap"] < df["ff_me_80"]),
        "mcap_qnt",
    ] = 3

    df.loc[df["mcap"] >= df["ff_me_80"], "mcap_qnt"] = 4
    # drop the size_bp columns
    df = df.drop(
        columns=[
            "ff_me_20",
            "ff_me_40",
            "ff_me_60",
            "ff_me_80",
        ]
    )

    return df


def load_gic(df, path: Path) -> pd.DataFrame:
    """
    Loads the GIC dataset from compustat.
    """
    gic = pd.read_parquet(get_latest_file(path / "compustat_gic_codes.parquet"))
    gic["indthru"] = gic["indthru"].fillna(pd.to_datetime(CRSP_END_DATE))
    gic = gic[["gvkey", "gsector", "ggroup", "indfrom", "indthru"]]

    df = df.merge(gic, on="gvkey", how="left")
    df = df[df["date"].between(df["indfrom"], df["indthru"])]

    return df.drop(columns=["indfrom", "indthru"])


def load_macro_ann_data(df: pd.DataFrame, path: Path) -> pd.DataFrame:
    """
    Loads the macro announcement data.
    """
    macro_ann = pd.read_excel(path / "macro_announcement_dates.xlsx")
    macro_ann = macro_ann.drop(columns="pre_94_fomc")

    for ann in macro_ann.columns:
        ann_date = macro_ann[[ann]].dropna()
        ann_date[ann] = pd.to_datetime(ann_date[ann], format="%m/%d/%Y")
        ann_date = ann_date.rename(columns={ann: "date"})
        ann_date[ann] = 1

        # merge on date
        df = df.merge(ann_date, on="date", how="left")
        df[ann] = df[ann].fillna(0)

    return df


def load_vix_data(df: pd.DataFrame, path: Path) -> pd.DataFrame:
    vix = pd.read_parquet(get_latest_file(path / "vix_daily.parquet"))
    vix["delta_vix"] = vix["vix"].diff()
    return df.merge(vix, on="date", how="left")


def clean_panel_data(df: pd.DataFrame, path: Path) -> None:
    # additional year, month, day columns
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month

    # Convert date to end of month
    df["year_month"] = df["date"] + pd.offsets.MonthEnd(0)

    # remove obs with no returns
    df = df[df["ret"].notna()]
    df = df[df["prc"].notna()]
    # compute overnight returns
    # open to close returns
    df["ret_oc"] = (df["prc"] - df["openprc"]) / df["openprc"]
    # overnight returns
    df["ret_on"] = (1 + df["ret"]) / (1 + df["ret_oc"]) - 1
    df["abs_ret"] = df["ret"].abs()
    df["abn_ret"] = df["ret"] - df["mkt"]
    df["neg_ret"] = (df["ret"] < 0).astype(int)
    df["neg_abn_ret"] = (df["abn_ret"] < 0).astype(int)
    df["abs_abn_ret"] = df["abn_ret"].abs()
    # market capitalization
    df["mcap"] = df["prc"] * df["shrout"] * 1000
    df["ln_mcap"] = np.log(df["mcap"])
    df = assign_mcap_breakpoints(df)

    # fillna for earnings announcement
    df["ea"] = df["ea"].fillna(0)

    # keep stocks with gsector
    df = df[df["gsector"].notna()]

    # Add dummy for monday to friday
    df["day_mon"] = (df["date"].dt.dayofweek == 0).astype(int)
    df["day_tue"] = (df["date"].dt.dayofweek == 1).astype(int)
    df["day_wed"] = (df["date"].dt.dayofweek == 2).astype(int)
    df["day_thu"] = (df["date"].dt.dayofweek == 3).astype(int)
    df["day_fri"] = (df["date"].dt.dayofweek == 4).astype(int)

    # remove weekends from df
    df = df[df["date"].dt.dayofweek < 5]

    # by permno, compute cumulative returns over the past 5 days
    df = df.sort_values(["permno", "date"])
    df["ln_ret"] = np.log(1 + df["ret"])

    return df


def build_panel(
    download_dir: Path, open_dir: Path, restricted_dir: Path, clean_dir: Path
) -> None:
    """
    Main function to process the panel data.
    """

    df = load_crsp_file(download_dir)
    df = load_gic(df, download_dir)
    print(len(df), "rows after loading ravenpack data")
    print(len(df), "rows after loading wsj full articles")
    df = load_fama_french_returns_data(df, open_dir)
    df = load_fama_french_me_breakpoints(df, open_dir)
    df = load_ibes_data(df, restricted_dir)
    df = load_ibes_analyst_coverage_data(df, restricted_dir)
    df = load_macro_ann_data(df, open_dir)
    df = load_vix_data(df, download_dir)

    return clean_panel_data(df, clean_dir)
