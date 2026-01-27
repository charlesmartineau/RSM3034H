from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats


def plot_event_study_earnings(panel: pd.DataFrame, fig_dir: Path) -> None:
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
    post_window = 60
    total_window = pre_window + post_window + 1

    # Ensure data is sorted by firm and date
    df = panel.sort_values(['permno', 'date']).reset_index(drop=True)

    # Create a row number within each firm for easy indexing
    df['row_num'] = df.groupby('permno').cumcount()

    # Identify earnings announcement dates
    ea_events = df[df['ea'] == 1][['permno', 'date', 'row_num', 'sue', 'mcap_qnt']].copy()
    ea_events = ea_events.rename(columns={'date': 'ea_date', 'row_num': 'ea_row'})
    ea_events['sue_qnt'] = pd.qcut(ea_events['sue'], 5, labels=False)

    ea_events = ea_events[ea_events['ea_date'].dt.year >= 2020]

    # Build the event window data
    bhar_data = []

    for _, event in ea_events.iterrows():
        permno = event['permno']
        ea_row = event['ea_row']
        sue_qnt = event['sue_qnt']
        ea_date = event['ea_date']
        mcap_qnt = event['mcap_qnt']

        # Get the firm's data
        firm_data = df[df['permno'] == permno].copy()

        # Define the window bounds
        start_row = ea_row - pre_window
        end_row = ea_row + post_window

        # Skip if window extends beyond available data
        if start_row < 0 or end_row >= len(firm_data):
            continue

        # Extract the window
        window_data = firm_data[(firm_data['row_num'] >= start_row) &
                                (firm_data['row_num'] <= end_row)].copy()

        if len(window_data) != total_window:
            continue

        # Calculate event day relative to announcement
        window_data['event_day'] = window_data['row_num'] - ea_row

        # Calculate cumulative returns (buy-and-hold)
        # BHAR = product(1 + ret) - product(1 + mkt)
        window_data = window_data.sort_values('event_day')
        window_data['cum_ret'] = (1 + window_data['ret']).cumprod() - 1
        window_data['cum_mkt'] = (1 + window_data['mkt']).cumprod() - 1
        window_data['bhar'] = window_data['cum_ret'] - window_data['cum_mkt']
        window_data['sue_qnt'] = sue_qnt
        window_data['ea_date'] = ea_date
        window_data['mcap_qnt'] = mcap_qnt

        bhar_data.append(window_data[['permno', 'event_day', 'bhar', 'sue_qnt', 'ea_date', 'mcap_qnt']])

    # Combine all events
    bhar_df = pd.concat(bhar_data, ignore_index=True)

    # Plot 1: Average BHAR for small cap (mcap_qnt == 0)
    avg_bhar_small = bhar_df[bhar_df['mcap_qnt'] == 0].groupby('event_day')['bhar'].mean().reset_index()
    avg_bhar_small = avg_bhar_small.sort_values('event_day')

    fig1, ax1 = plt.subplots(figsize=(10, 6))
    ax1.plot(avg_bhar_small['event_day'], avg_bhar_small['bhar'], marker='o', markersize=4, linewidth=1.5)
    ax1.axhline(y=0, color='gray', linestyle='--', linewidth=0.8)
    ax1.axvline(x=0, color='red', linestyle='--', linewidth=0.8, label='Earnings Announcement')
    ax1.set_xlabel('Days Relative to Earnings Announcement')
    ax1.set_ylabel('Average Buy-and-Hold Abnormal Return (BHAR)')
    ax1.set_title('Average BHAR Around Earnings Announcements (Small Cap)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    plt.tight_layout()
    fig1.savefig(fig_dir / 'event_study_bhar_small_cap.png', dpi=300, bbox_inches='tight')
    plt.close(fig1)
    print(f"Figure saved to {fig_dir / 'event_study_bhar_small_cap.png'}")

    # Plot 2: Average BHAR for large cap (mcap_qnt > 0)
    avg_bhar_large = bhar_df[bhar_df['mcap_qnt'] > 0].groupby('event_day')['bhar'].mean().reset_index()
    avg_bhar_large = avg_bhar_large.sort_values('event_day')

    fig2, ax2 = plt.subplots(figsize=(10, 6))
    ax2.plot(avg_bhar_large['event_day'], avg_bhar_large['bhar'], marker='o', markersize=4, linewidth=1.5)
    ax2.axhline(y=0, color='gray', linestyle='--', linewidth=0.8)
    ax2.axvline(x=0, color='red', linestyle='--', linewidth=0.8, label='Earnings Announcement')
    ax2.set_xlabel('Days Relative to Earnings Announcement')
    ax2.set_ylabel('Average Buy-and-Hold Abnormal Return (BHAR)')
    ax2.set_title('Average BHAR Around Earnings Announcements (Large Cap)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    plt.tight_layout()
    fig2.savefig(fig_dir / 'event_study_bhar_large_cap.png', dpi=300, bbox_inches='tight')
    plt.close(fig2)
    print(f"Figure saved to {fig_dir / 'event_study_bhar_large_cap.png'}")

    # Plot 3: BHAR by earnings surprise quintile with 95% CI (small cap)
    def calc_stats(group):
        n = len(group)
        mean = group['bhar'].mean()
        se = group['bhar'].std() / np.sqrt(n)
        ci_95 = stats.t.ppf(0.975, n - 1) * se if n > 1 else 0
        return pd.Series({'mean_bhar': mean, 'ci_95': ci_95, 'n': n})

    bhar_by_quintile = bhar_df[bhar_df['mcap_qnt'] == 0].groupby(
        ['sue_qnt', 'event_day']
    ).apply(calc_stats).reset_index()

    fig3, ax3 = plt.subplots(figsize=(12, 7))
    colors = plt.cm.RdYlGn(np.linspace(0.1, 0.9, 5))
    quintile_labels = ['Q1 (Negative Surprise)', 'Q2', 'Q3', 'Q4', 'Q5 (Positive Surprise)']

    for q in range(5):
        q_data = bhar_by_quintile[bhar_by_quintile['sue_qnt'] == q].sort_values('event_day')
        ax3.plot(q_data['event_day'], q_data['mean_bhar'],
                 color=colors[q], linewidth=1.5, label=quintile_labels[q])
        ax3.fill_between(q_data['event_day'],
                         q_data['mean_bhar'] - q_data['ci_95'],
                         q_data['mean_bhar'] + q_data['ci_95'],
                         color=colors[q], alpha=0.2)

    ax3.axhline(y=0, color='gray', linestyle='--', linewidth=0.8)
    ax3.axvline(x=0, color='black', linestyle='--', linewidth=0.8)
    ax3.set_xlabel('Days Relative to Earnings Announcement')
    ax3.set_ylabel('Average Buy-and-Hold Abnormal Return (BHAR)')
    ax3.set_title('Average BHAR by Earnings Surprise Quintile (Small Cap)')
    ax3.legend(loc='upper left')
    ax3.grid(True, alpha=0.3)
    plt.tight_layout()
    fig3.savefig(fig_dir / 'event_study_bhar_by_surprise_quintile.png', dpi=300, bbox_inches='tight')
    plt.close(fig3)
    print(f"Figure saved to {fig_dir / 'event_study_bhar_by_surprise_quintile.png'}")
