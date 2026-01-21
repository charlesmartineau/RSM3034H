import pandas as pd


def get_vrp_monthly() -> pd.DataFrame:
    """
    Download VRP (Variance Risk Premium) monthly data from Google Drive.

    The data contains Year and Month columns which are combined into a date column
    at the end of each month.
    """
    # Google Drive file ID extracted from the share link
    file_id = "1PwH5qb0nrvrfWqObN_X4DqruJapFBbAp"
    url = f"https://drive.google.com/uc?id={file_id}&export=download"

    # Read the txt file (whitespace-separated)
    vrp = pd.read_csv(url, sep=r"\s+")

    # Create date column from Year and Month, set to end of month
    vrp["date"] = pd.to_datetime(
        vrp["Year"].astype(str) + "-" + vrp["Month"].astype(str) + "-01"
    ) + pd.offsets.MonthEnd(0)

    vrp.columns = vrp.columns.str.lower()

    return vrp[["date", "vrp"]]
