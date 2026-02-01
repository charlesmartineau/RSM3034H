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


def get_ff_bm_bp() -> pd.DataFrame:
    """
    Download the NYSE B/M breakpoints data from Kenneth R. French's website and return a DataFrame.
    """
    ff_url = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/BE-ME_Breakpoints_CSV.zip"

    response = requests.get(ff_url)

    with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
        with zip_file.open("BE-ME_Breakpoints.csv") as csv_file:
            bp = pd.read_csv(csv_file, skiprows=3, header=None)
            # bp = bp[:-1] # remove row with the copyright info
            # remove the columns with the counts of obs which are column # 1 # 2 and # 3
            bp = bp.drop(columns=[1, 2])
            bp.columns = ["date"] + [f"bm_bp{i}" for i in range(1, 21)]
            bp = bp[~bp["date"].str.startswith("Copyright")]

            bp["date"] = pd.to_datetime(bp["date"], format="%Y")
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


def get_ff_25_size_bm_portfolios_daily() -> pd.DataFrame:
    """
    Download the Fama-French 25 size and B/M portfolios daily returns data and return a DataFrame.
    """
    ff_url = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/25_Portfolios_5x5_Daily_CSV.zip"
    response = requests.get(ff_url)
    with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
        with zip_file.open("25_Portfolios_5x5_Daily.csv") as csv_file:
            port = pd.read_csv(csv_file, skiprows=18)
            port = port.rename(columns={"Unnamed: 0": "date"})
            # find index that includes "Average Equal" in column date and drop all rows after that
            port = port[
                port["date"].notna()
            ]  # remove rows with NaN in date column to do the next step
            avg_equal_index = port[port["date"].str.contains("Average Equal")].index[0]
            port = port.iloc[:avg_equal_index]

            # rename columns to have size_bp and bm_bp
            port = port.rename(
                columns={
                    "SMALL LoBM": "ff_size1_bm1",
                    "ME1 BM2": "ff_size1_bm2",
                    "ME1 BM3": "ff_size1_bm3",
                    "ME1 BM4": "ff_size1_bm4",
                    "SMALL HiBM": "ff_size1_bm5",
                    "ME2 BM1": "ff_size2_bm1",
                    "ME2 BM2": "ff_size2_bm2",
                    "ME2 BM3": "ff_size2_bm3",
                    "ME2 BM4": "ff_size2_bm4",
                    "ME2 BM5": "ff_size2_bm5",
                    "ME3 BM1": "ff_size3_bm1",
                    "ME3 BM2": "ff_size3_bm2",
                    "ME3 BM3": "ff_size3_bm3",
                    "ME3 BM4": "ff_size3_bm4",
                    "ME3 BM5": "ff_size3_bm5",
                    "ME4 BM1": "ff_size4_bm1",
                    "ME4 BM2": "ff_size4_bm2",
                    "ME4 BM3": "ff_size4_bm3",
                    "ME4 BM4": "ff_size4_bm4",
                    "ME4 BM5": "ff_size4_bm5",
                    "BIG LoBM": "ff_size5_bm1",
                    "ME5 BM2": "ff_size5_bm2",
                    "ME5 BM3": "ff_size5_bm3",
                    "ME5 BM4": "ff_size5_bm4",
                    "BIG HiBM": "ff_size5_bm5",
                }
            )
            # annual dates have 2 blank spaces before the year
            port["date"] = port["date"].str.strip()
            port = port[port["date"].str.len() == 8]

            port["date"] = pd.to_datetime(
                port["date"], format="%Y%m%d"
            ) 
            # divide by 100 the returns since the returns are in % in the csv file
            for col in port.columns[1:]:
                port[col] = port[col].astype(float)
                port[col] = port[col] / 100
            return port
