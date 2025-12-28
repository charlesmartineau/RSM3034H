import pandas as pd
import yfinance as yf


def get_vix_daily() -> pd.DataFrame:
    """
    Download VIX daily data from Yahoo Finance and return a DataFrame.
    """
    vix = yf.download("^VIX", period="max", interval="1d", progress=False)

    # Reset index to have date as a column
    vix = vix.reset_index()
    vix.columns = ["date", "close", "high", "low", "open", "volume"]

    # Keep only the date and close price (VIX level)
    vix = vix[["date", "close"]].rename(columns={"close": "vix"})

    # Ensure date is datetime
    vix["date"] = pd.to_datetime(vix["date"])

    return vix
