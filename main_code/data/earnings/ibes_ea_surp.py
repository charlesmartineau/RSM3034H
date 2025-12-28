# SAME CODE FROM PAPER WITH EDNA
# %%
import datetime
import os
from pathlib import Path
from ..utils import get_latest_file

import numpy as np
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
# %%
data_dir = Path(os.getenv("DATADIR"))
download_dir = data_dir / "download_cache/"
open_dir = data_dir / "open/"
restricted_dir = data_dir / "restricted/"
clean_dir = data_dir / "clean/"


def load_compustat_fundq(path: Path, constraint: bool = True) -> pd.DataFrame:
    """
    Retrieve Compustat quarterly fundamental data.
    """

    fundq = pd.read_parquet(get_latest_file(path / "compustat_quarterly.parquet"))
    # impove total assets >0, no missing sales and datafqtr
    if constraint:
        return fundq.loc[
            ((fundq.atq > 0) | (fundq.saleq.notna())) & (fundq.datafqtr.notna())
        ]
    else:
        return fundq


def merge_link_tables(
    path: Path, end_date: str, score_mapping: int = 1
) -> pd.DataFrame:
    """
    Retrieve the CRSP-Compustat link table and merge it with the IBES link table.

    Args:
        restricted_dir (Path): path to save directory
        end_date (str): the end data of the sample period that replaces the NaT values in the linkenddt column
        score_mapping (int): the maximum "matching" score to keep in the IBES link table. See code iclink.py for details.

    Returns:
        pd.DataFrame: _description_
    """

    # Load the iclink data
    iclink = pd.read_parquet(get_latest_file(path / "ibes/iclink.parquet"))
    iclink = iclink[iclink["score"] <= score_mapping]

    # load crsp-gvkey link
    gvkey_link = pd.read_parquet(get_latest_file(path / "crsp_compu_link_table.parquet"))
    gvkey_link = gvkey_link.rename(columns={"lpermno": "permno"})
    gvkey_link = gvkey_link[["gvkey", "permno", "linkdt", "linkenddt"]]
    gvkey_link["linkenddt"] = gvkey_link["linkenddt"].fillna(
        pd.to_datetime(end_date, format="%m/%d/%Y")
    )
    iclink = iclink[["ticker", "permno"]].drop_duplicates()

    return pd.merge(iclink, gvkey_link, how="left", on="permno")


"""
Get IBES surprises and earnings announcement dates.
Code is adapted https://www.fredasongdrechsler.com/data-crunching/pead
"""

end_date: str = "12/31/2024"

# retrieve link  table
link = merge_link_tables(restricted_dir, end_date)
# load analyst estimates
ibes_ana_est = pd.read_parquet(
    get_latest_file(download_dir / "ibes_estimates.parquet")
)

# Merge the iclink data
ibes_ana_est = pd.merge(ibes_ana_est, link, how="left", on="ticker")
# Keep stocks for which the announcement date is between the linkdt and linkenddt
ibes_ana_est = ibes_ana_est.loc[
    (ibes_ana_est["linkdt"] <= ibes_ana_est["anndats"])
    & (ibes_ana_est["anndats"] <= ibes_ana_est["linkenddt"])
]

# Count number of estimates reported on primary/diluted basis
p_sub = ibes_ana_est[["ticker", "fpedats", "pdf"]].loc[ibes_ana_est.pdf == "P"]
d_sub = ibes_ana_est[["ticker", "fpedats", "pdf"]].loc[ibes_ana_est.pdf == "D"]

p_count = (
    p_sub.groupby(["ticker", "fpedats"])
    .pdf.count()
    .reset_index()
    .rename(columns={"pdf": "p_count"})
)
d_count = (
    d_sub.groupby(["ticker", "fpedats"])
    .pdf.count()
    .reset_index()
    .rename(columns={"pdf": "d_count"})
)

ibes = pd.merge(ibes_ana_est, d_count, how="left", on=["ticker", "fpedats"])
ibes = pd.merge(ibes, p_count, how="left", on=["ticker", "fpedats"])
ibes["d_count"] = ibes.d_count.fillna(0)
ibes["p_count"] = ibes.p_count.fillna(0)

# Determine whether most analysts report estimates on primary/diluted basis
# following Livnat and Mendenhall (2006)

ibes["basis"] = np.where(ibes.p_count > ibes.d_count, "P", "D")

ibes = ibes.sort_values(
    by=[
        "ticker",
        "fpedats",
        "estimator",
        "analys",
        "anndats",
        "anntims",
        "revdats",
        "revtims",
    ]
).drop(columns=["p_count", "d_count", "pdf", "fpi"])

# Keep the latest observation for a given analyst
# Group by company fpedats estimator analys then pick the last record in the group

ibes = ibes.groupby(["ticker", "fpedats", "estimator", "analys"]).last().reset_index()

# Link Estimates with Actuals #
# Link Unadjusted estimates with Unadjusted actuals and CRSP permnos
# Keep only the estimates issued within 90 days before the report date

# Getting actual piece of data
ibes_act = pd.read_parquet(restricted_dir / "ibes/ibes_actuals.parquet")
# Create datetime columns
ibes_act["datetime"] = pd.to_datetime(
    ibes_act["repdats"].astype(str) + " " + ibes_act["repdats_time"].astype(str)
)
ibes_act = ibes_act.drop(columns=["repdats_time"])

# Join with the estimate piece of the data
ibes1 = pd.merge(ibes, ibes_act, how="left", on=["ticker", "fpedats"])
ibes1["dgap"] = ibes1.repdats - ibes1.anndats

ibes1["flag"] = np.where(
    (ibes1["dgap"] >= datetime.timedelta(days=0))
    & (ibes1["dgap"] <= datetime.timedelta(days=90))
    & (ibes1["repdats"].notna())
    & (ibes1["anndats"].notna()),
    1,
    0,
)

ibes1 = ibes1[ibes1.flag == 1].drop(columns=["flag", "dgap", "pdicity"])

# Select all relevant combinations of Permnos and Date
ibes1_dt1 = ibes1[["permno", "anndats"]].drop_duplicates()
ibes1_dt2 = (
    ibes1[["permno", "repdats"]]
    .drop_duplicates()
    .rename(columns={"repdats": "anndats"})
)
ibes_anndats = pd.concat([ibes1_dt1, ibes1_dt2]).drop_duplicates()

# Adjust all estimate and earnings announcement dates to the closest
# preceding trading date in CRSP to ensure that adjustment factors won't
# be missing after the merge

# unique anndats from ibes
uniq_anndats = ibes_anndats[["anndats"]].drop_duplicates()

# unique trade dates from crsp.dsi
crsp_dats = pd.read_parquet(restricted_dir / "crsp/crsp_dates.parquet")

# Create up to 5 days prior dates relative to anndats

for i in range(0, 5):
    uniq_anndats[i] = uniq_anndats.anndats - datetime.timedelta(days=i)

# reshape (transpose) the df for later join with crsp trading dates

expand_anndats = (
    uniq_anndats.set_index("anndats")
    .stack()
    .reset_index()
    .rename(columns={"level_1": "prior", 0: "prior_date"})
)

# merge with crsp trading dates
tradedates = pd.merge(
    expand_anndats, crsp_dats, how="left", left_on=["prior_date"], right_on=["date"]
)

# create the dgap (days gap) variable for min selection
tradedates["dgap"] = tradedates["anndats"] - tradedates["date"]

# choosing the row with the smallest dgap for a given anndats
tradedates = tradedates.sort_values(by=["anndats", "dgap"])
tradedates = tradedates[tradedates["dgap"].notnull()]
tradedates = tradedates.loc[tradedates.groupby("anndats")["dgap"].idxmin()]
tradedates = tradedates[["anndats", "date"]]

# merge the CRSP adjustment factors for all estimate and report dates
# extract CRSP adjustment factors
cfacshr = pd.read_parquet(restricted_dir / "crsp/crsp_cfacshr.parquet")
# Keep only the relevant columns

ibes_anndats = pd.merge(ibes_anndats, tradedates, how="left", on=["anndats"])
ibes_anndats = pd.merge(ibes_anndats, cfacshr, how="left", on=["permno", "date"])

# Adjust Estimates with CFACSHR from crsp
# Put the estimate on the same per share basis as
# company reported EPS using CRSP Adjustment factors.
# New_value is the estimate adjusted to be on the same basis with reported earnings.

ibes1 = pd.merge(ibes1, ibes_anndats, how="inner", on=["permno", "anndats"])
ibes1 = ibes1.drop(["anndats", "date"], axis=1).rename(
    columns={"cfacshr": "cfacshr_ann"}
)

ibes1 = pd.merge(
    ibes1,
    ibes_anndats,
    how="inner",
    left_on=["permno", "repdats"],
    right_on=["permno", "anndats"],
)
ibes1 = ibes1.drop(["anndats", "date"], axis=1).rename(
    columns={"cfacshr": "cfacshr_rep"}
)

ibes1["new_value"] = (ibes1["cfacshr_rep"] / ibes1["cfacshr_ann"]) * ibes1["value"]

# Sanity check: there should be one most recent estimate for
# a given firm-fiscal period end combination
ibes1 = ibes1.sort_values(
    by=["ticker", "fpedats", "estimator", "analys"]
).drop_duplicates()

# Compute the median forecast based on estimates in the 90 days prior to the EAD
grp_permno = (
    ibes1.groupby(["ticker", "fpedats", "basis", "repdats", "datetime", "act"])[
        "permno"
    ]
    .first()
    .reset_index()
)

# compute analyst dispersion using std of the forecast
disp = ibes1.copy()
disp["forecast_disp"] = disp["act"] - disp["new_value"]
disp = (
    disp.groupby(["ticker", "fpedats", "basis", "repdats", "datetime", "act"])[
        "forecast_disp"
    ]
    .agg(["std"])
    .reset_index()
    .rename(columns={"std": "forecast_disp_std"})
)

disp2 = ibes1.groupby(["ticker", "fpedats", "basis", "repdats", "datetime", "act"])[
    "new_value"
].agg(["max", "min", "mean"])
disp2["forecast_disp_max_min"] = (disp2["max"] - disp2["min"]) / disp2["mean"]

# merge the dispersion with the median estimates
disp = pd.merge(
    disp, disp2, how="inner", on=["ticker", "fpedats", "basis", "repdats", "datetime"]
)

disp = disp[
    [
        "ticker",
        "fpedats",
        "basis",
        "repdats",
        "datetime",
        "act",
        "forecast_disp_std",
        "forecast_disp_max_min",
    ]
].drop_duplicates()


# new_value is the estimate adjusted to be on the same basis with reported earnings by analyst
medest = (
    ibes1.groupby(["ticker", "fpedats", "basis", "repdats", "datetime", "act"])[
        "new_value"
    ]
    .agg(["median", "count"])
    .reset_index()
)
medest = pd.merge(
    medest,
    grp_permno,
    how="inner",
    on=["ticker", "fpedats", "basis", "repdats", "datetime", "act"],
)
medest = medest.rename(columns={"median": "medest", "count": "numest"})

# Merge with Compustat Data  #
# get items from fundq
fundq = pd.read_parquet(get_latest_file(download_dir / "compustat_quarterly.parquet"))
# Keep only

# Calculate link date ranges for givken gvkey and ticker combination
gvkey_mindt1 = (
    link.groupby(["gvkey", "ticker"])
    .linkdt.min()
    .reset_index()
    .rename(columns={"linkdt": "mindate"})
)
gvkey_maxdt1 = (
    link.groupby(["gvkey", "ticker"])
    .linkenddt.max()
    .reset_index()
    .rename(columns={"linkenddt": "maxdate"})
)
gvkey_dt1 = pd.merge(gvkey_mindt1, gvkey_maxdt1, how="inner", on=["gvkey", "ticker"])

# Use the date range to merge
comp = pd.merge(fundq, gvkey_dt1, how="left", on=["gvkey"])
comp = comp.loc[
    (comp["ticker"].notna())
    & (comp["datadate"] <= comp["maxdate"])
    & (comp["datadate"] >= comp["mindate"])
]

# Merge with the median estimates
comp = pd.merge(
    comp,
    medest,
    how="left",
    left_on=["ticker", "datadate"],
    right_on=["ticker", "fpedats"],
)

# merge comp with the dispersion
comp = pd.merge(
    comp,
    disp[["ticker", "fpedats", "basis", "forecast_disp_std", "forecast_disp_max_min"]],
    how="left",
    on=["ticker", "fpedats", "basis"],
)

# Sort data and drop duplicates
comp = comp.sort_values(by=["gvkey", "fqtr", "fyearq"]).drop_duplicates()

# Step 6. Calculate SUEs  #
# block handling lag eps

sue = comp.sort_values(by=["gvkey", "fqtr", "fyearq"])

sue["dif_fyearq"] = sue.groupby(["gvkey", "fqtr"])["fyearq"].diff()
sue["laggvkey"] = sue["gvkey"].shift(1)

# handling same qtr previous year

cond_year = (sue["dif_fyearq"] == 1).fillna(False)  # year increment is 1
sue["lagadj"] = np.where(cond_year, sue["ajexq"].shift(1), None)
sue["lageps_p"] = np.where(cond_year, sue["epspxq"].shift(1), None)
sue["lageps_d"] = np.where(cond_year, sue["epsfxq"].shift(1), None)
sue["lagshr_p"] = np.where(cond_year, sue["cshprq"].shift(1), None)
sue["lagshr_d"] = np.where(cond_year, sue["cshfdq"].shift(1), None)
sue["lagspiq"] = np.where(cond_year, sue["spiq"].shift(1), None)

# handling first gvkey
cond_gvkey = (sue["gvkey"] != sue["laggvkey"]).fillna(False)  # first.gvkey

sue["lagadj"] = np.where(cond_gvkey, None, sue["lagadj"])
sue["lageps_p"] = np.where(cond_gvkey, None, sue["lageps_p"])
sue["lageps_d"] = np.where(cond_gvkey, None, sue["lageps_d"])
sue["lagshr_p"] = np.where(cond_gvkey, None, sue["lagshr_p"])
sue["lagshr_d"] = np.where(cond_gvkey, None, sue["lagshr_d"])
sue["lagspiq"] = np.where(cond_gvkey, None, sue["lagspiq"])

# handling reporting basis
# Basis = P and missing are treated the same
sue["actual1"] = np.where(
    sue["basis"] == "D", sue["epsfxq"] / sue["ajexq"], sue["epspxq"] / sue["ajexq"]
)

sue["actual2"] = np.where(
    sue["basis"] == "D",
    (sue["epsfxq"].fillna(0) - (0.65 * sue["spiq"] / sue["cshfdq"]).fillna(0))
    / sue["ajexq"],
    (sue["epspxq"].fillna(0) - (0.65 * sue["spiq"] / sue["cshprq"]).fillna(0))
    / sue["ajexq"],
)

sue["expected1"] = np.where(
    sue["basis"] == "D",
    sue["lageps_d"] / sue["lagadj"],
    sue["lageps_p"] / sue["lagadj"],
)
sue["expected2"] = np.where(
    sue["basis"] == "D",
    (sue["lageps_d"].fillna(0) - (0.65 * sue["lagspiq"] / sue["lagshr_d"]).fillna(0))
    / sue["lagadj"],
    (sue["lageps_p"].fillna(0) - (0.65 * sue["lagspiq"] / sue["lagshr_p"]).fillna(0))
    / sue["lagadj"],
)

# SUE calculations
# sue["sue1"] = (sue["actual1"] - sue["expected1"]) / (sue["prccq"] / sue["ajexq"])
# sue["sue2"] = (sue["actual2"] - sue["expected2"]) / (sue["prccq"] / sue["ajexq"])
sue["sue3"] = (sue["act"] - sue["medest"]) / sue["prccq"]

sue = sue[
    [
        "ticker",
        "permno",
        "gvkey",
        "conm",
        "fpedats",
        "fyearq",
        "fqtr",
        "fyr",
        "datadate",
        "datetime",
        "repdats",
        "rdq",
        #        "sue1",
        #        "sue2",
        "sue3",
        "forecast_disp_std",
        "forecast_disp_max_min",
        "basis",
        "act",
        "medest",
        "numest",
        "prccq",
        "mcap",
    ]
]

# Shifting the announcement date to be the next trading day
# Defining the day after the following quarterly EA as leadrdq1

# unique rdq
uniq_rdq = comp[["rdq"]].drop_duplicates()

# Create up to 5 days post rdq relative to rdq
for i in range(5):
    uniq_rdq[i] = uniq_rdq["rdq"] + datetime.timedelta(days=i)

# reshape (transpose) for later join with crsp trading dates
expand_rdq = (
    uniq_rdq.set_index("rdq")
    .stack()
    .reset_index()
    .rename(columns={"level_1": "post", 0: "post_date"})
)

# merge with crsp trading dates
eads1 = pd.merge(
    expand_rdq, crsp_dats, how="left", left_on=["post_date"], right_on=["date"]
)

# create the dgap (days gap) variable for min selection
eads1["dgap"] = eads1.date - eads1.rdq

# LOC deprecated, use reindex instead
eads1 = eads1[eads1["dgap"].notnull()]
eads1 = eads1.reindex(eads1.groupby("rdq")["dgap"].idxmin()).rename(
    columns={"date": "rdq1"}
)

# create sue_final
sue_final = pd.merge(sue, eads1[["rdq", "rdq1"]], how="left", on=["rdq"])
sue_final = sue_final.sort_values(
    by=["gvkey", "fyearq", "fqtr"], ascending=[True, False, False]
).drop_duplicates()

# Impose the filters from Livnat & Mendenhall (2006):
# - earnings announcement date is reported in Compustat
# - the price per share is available from Compustat at fiscal quarter end
# - price is greater than $1
# - the market (book) equity at fiscal quarter end is available and is
# EADs in Compustat and in IBES (if available) should not differ by more than one calendar day larger and MCAP > $5 mil.

sue_final["leadrdq1"] = sue_final.rdq1.shift(1)  # next consecutive EAD
sue_final["leadgvkey"] = sue_final.gvkey.shift(1)

# If first gvkey then leadrdq1 = rdq1+3 months
# Else leadrdq1 = previous rdq1
cond = (sue_final["gvkey"] == sue_final["leadgvkey"]).fillna(False)  # first gvkey
sue_final["leadrdq1"] = np.where(
    cond,
    sue_final["rdq1"].shift(1),
    sue_final["rdq1"] + pd.DateOffset(months=3),
)

sue_final["dgap"] = (sue_final["repdats"] - sue_final["rdq"]).fillna(
    pd.Timedelta(days=0)
)
sue_final = sue_final.loc[(sue_final["rdq1"] != sue_final["leadrdq1"])]

# Various conditioning for filtering
# cond1 = (
#    (sue_final["sue1"].notna())
#    & (sue_final["sue2"].notna())
#    & (sue_final["repdats"].isna())
# )
cond2 = (
    (sue_final["repdats"].notna())
    & (sue_final["dgap"] <= datetime.timedelta(days=1))
    & (sue_final["dgap"] >= datetime.timedelta(days=-1))
)
# sue_final = sue_final.loc[cond1 | cond2]
sue_final = sue_final.loc[cond2]

# Impose restriction on price and marketcap
# sue_final = sue_final.loc[(sue_final.rdq.notna()) & (sue_final.prccq>1) & (sue_final.mcap>5)]
sue_final = sue_final.loc[(sue_final.rdq.notna())]

# Keep relevant columns
sue_final = sue_final[
    [
        "gvkey",
        "ticker",
        "permno",
        "conm",
        "datetime",
        "fpedats",
        "rdq",
        "rdq1",
        "datadate",
        "leadrdq1",
        "repdats",
        "mcap",
        "medest",
        "act",
        "numest",
        #        "sue1",
        #        "sue2",
        "sue3",
        "forecast_disp_std",
        "forecast_disp_max_min",
    ]
]

# rename sue
sue_final = sue_final.rename(
    columns={"sue1": "sue_rw1", "sue2": "sue_rw2", "sue3": "sue"}
)

sue_final.to_parquet(restricted_dir / "ibes/ibes_sue.parquet", index=False)
