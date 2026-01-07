import io
import zipfile

import pandas as pd
import requests


def get_ff_size_bp() -> pd.DataFrame:
    """
    Download the NYSE breakpoints data from Kenneth R. French's website and return a DataFrame.
    """
    ff_url = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/ME_Breakpoints_CSV.zip"

    response = requests.get(ff_url)

    with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
        with zip_file.open("ME_Breakpoints.csv") as csv_file:
            bp = pd.read_csv(csv_file, skiprows=1, header=None)
            bp = bp[:-1]
            bp.columns = ["date", "n"] + [f"size_bp{i}" for i in range(1, 21)]
            bp = bp[~bp["date"].str.startswith("Copyright")]

            bp["date"] = pd.to_datetime(
                bp["date"], format="%Y%m"
            ) + pd.offsets.MonthEnd(0)
            bp = bp.drop(columns=["n"])
            # multiply by 1,000,000 since the breakpoints are in millions of dollars
            bp[bp.columns[1:]] = bp[bp.columns[1:]] * 1000000
            return bp


def get_ff5_factors() -> pd.DataFrame:
    """
    Download the Fama-French 5 factors data from Kenneth R. French's website and return a DataFrame.
    """
    ff_url = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_5_Factors_2x3_daily_CSV.zip"
    response = requests.get(ff_url)
    with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
        with zip_file.open("F-F_Research_Data_5_Factors_2x3_daily.csv") as csv_file:
            ff5 = pd.read_csv(csv_file, skiprows=4)
            ff5 = ff5.rename(
                columns={
                    "Unnamed: 0": "date",
                    "Mkt-RF": "mkt_rf",
                    "SMB": "smb",
                    "HML": "hml",
                    "RMW": "rmw",
                    "CMA": "cma",
                    "RF": "rf",
                }
            )
            # remove row in column "date" that starts with "Copyright"
            ff5 = ff5[~ff5["date"].str.startswith("Copyright")]
            ff5["date"] = pd.to_datetime(ff5["date"], format="%Y%m%d")
            # divide by 100 the returns since the returns are in % in the csv file
            ff5[["mkt_rf", "smb", "hml", "rmw", "cma", "rf"]] = (
                ff5[["mkt_rf", "smb", "hml", "rmw", "cma", "rf"]] / 100
            )
            return ff5


def get_ff5_factors_monthly() -> pd.DataFrame:
    """
    Download the Fama-French 5 factors monthly data from Kenneth R. French's website and return a DataFrame.
    """
    ff_url = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_5_Factors_2x3_CSV.zip"
    response = requests.get(ff_url)
    with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
        with zip_file.open("F-F_Research_Data_5_Factors_2x3.csv") as csv_file:
            ff5 = pd.read_csv(csv_file, skiprows=4)
            ff5 = ff5.rename(
                columns={
                    "Unnamed: 0": "date",
                    "Mkt-RF": "mkt_rf",
                    "SMB": "smb",
                    "HML": "hml",
                    "RMW": "rmw",
                    "CMA": "cma",
                    "RF": "rf",
                }
            )
            # remove annual data
            # annual dates have 2 blank spaces before the year
            ff5["date"] = ff5["date"].str.strip()
            # keep only monthly freq data
            ff5 = ff5[ff5["date"].str.len() == 6]
            ff5 = ff5[~ff5["date"].str.startswith("Copyright")]

            ff5["date"] = pd.to_datetime(
                ff5["date"], format="%Y%m"
            ) + pd.offsets.MonthEnd(0)
            # divide by 100 the returns since the returns are in % in the csv file
            for col in ["mkt_rf", "smb", "hml", "rmw", "cma", "rf"]:
                ff5[col] = ff5[col].astype(float)
                ff5[col] = ff5[col] / 100
            return ff5


def get_ff_umd_factor_monthly() -> pd.DataFrame:
    """
    Download the Fama-French UMD momentum factor data and return a DataFrame.
    """
    ff_url = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Momentum_Factor_CSV.zip"
    response = requests.get(ff_url)
    with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
        with zip_file.open("F-F_Momentum_Factor.csv") as csv_file:
            mom = pd.read_csv(csv_file, skiprows=13)
            mom.columns = ["date", "mom"]
            # annual dates have 2 blank spaces before the year
            mom["date"] = mom["date"].str.strip()
            mom = mom[mom["date"].str.len() == 6]

            mom["date"] = pd.to_datetime(
                mom["date"], format="%Y%m"
            ) + pd.offsets.MonthEnd(0)
            # divide by 100 the returns since the returns are in % in the csv file
            mom["mom"] = mom["mom"].astype(float)
            mom["mom"] = mom["mom"] / 100
            return mom
