import pandas as pd


def build_event_earnings_data(panel: pd.DataFrame) -> None:
    """
    Create event study plots for earnings announcements showing BHAR.

    Parameters
    ----------
    panel : pd.DataFrame
        Panel dataset with columns: permno, date, ret, mkt, ea, sue, mcap_qnt
    fig_dir : Path
        Directory to save the figures
    """
    # Event study parameters
    pre_window = 10
    post_window = 62
    total_window = pre_window + post_window + 1

    # Ensure data is sorted by firm and date
    df = panel.sort_values(["permno", "date"]).reset_index(drop=True)

    # Create a row number within each firm for easy indexing
    df["row_num"] = df.groupby("permno").cumcount()

    # Identify earnings announcement dates
    ea_events = df[df["ea"] == 1][
        ["permno", "date", "row_num", "sue", "mcap", "mcap_qnt", "gsector"]
    ].copy()
    ea_events = ea_events.rename(columns={"date": "ea_date", "row_num": "ea_row"})
    ea_events["sue_qnt"] = pd.qcut(ea_events["sue"], 5, labels=False)

    ea_events = ea_events[ea_events["ea_date"].dt.year >= 2008]

    # Build the event window data
    event_data = []

    for _, event in ea_events.iterrows():
        permno = event["permno"]
        ea_row = event["ea_row"]
        sue_qnt = event["sue_qnt"]
        sue = event["sue"]
        ea_date = event["ea_date"]
        mcap = event["mcap"]
        mcap_qnt = event["mcap_qnt"]
        gsector = event["gsector"]

        # Get the firm's data
        firm_data = df[df["permno"] == permno].copy()

        # Define the window bounds
        start_row = ea_row - pre_window
        end_row = ea_row + post_window

        # Skip if window extends beyond available data
        if start_row < 0 or end_row >= len(firm_data):
            continue

        # Extract the window
        window_data = firm_data[
            (firm_data["row_num"] >= start_row) & (firm_data["row_num"] <= end_row)
        ].copy()

        if len(window_data) != total_window:
            continue

        # Calculate event day relative to announcement
        window_data["event_t"] = window_data["row_num"] - ea_row

        # Calculate cumulative returns (buy-and-hold)
        # BHAR = product(1 + ret) - product(1 + mkt)
        window_data = window_data.sort_values("event_t")
        window_data["sue_qnt"] = sue_qnt
        window_data["ea_date"] = ea_date
        window_data["mcap_qnt"] = mcap_qnt
        window_data["gsector"] = gsector
        window_data["mcap"] = mcap
        window_data["sue"] = sue

        event_data.append(
            window_data[
                [
                    "date",
                    "permno",
                    "gvkey",
                    "prc",
                    "openprc",
                    "ret",
                    "mkt",
                    "mkt_rf",
                    "smb",
                    "hml",
                    "rmw",
                    "cma",
                    "rf",
                    "ff_port",
                    "sue",
                    "sue_qnt",
                    "mcap",
                    "mcap_qnt",
                    "gsector",
                    "event_t",
                    "ea_date",
                ]
            ]
        )

    # Combine all events
    return pd.concat(event_data, ignore_index=True)
