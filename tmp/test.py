#%%
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats

df = pd.read_parquet("/Users/charles.martineau/Dropbox/Teaching/Rotman/RSM3034H/data/clean/panel_data_20260107_061812.parquet")

#%%
# Event study parameters
pre_window = 10
post_window = 60
total_window = pre_window + post_window + 1  # -10 to +60 inclusive

# Ensure data is sorted by firm and date
df = df.sort_values(['permno', 'date']).reset_index(drop=True)

# Create a row number within each firm for easy indexing
df['row_num'] = df.groupby('permno').cumcount()

# Identify earnings announcement dates
ea_events = df[df['ea'] == 1][['permno', 'date', 'row_num', 'sue', 'mcap_qnt']].copy()
ea_events = ea_events.rename(columns={'date': 'ea_date', 'row_num': 'ea_row'})
ea_events['sue_qnt'] = pd.qcut(ea_events['sue'], 5, labels=False)

ea_events = ea_events[ea_events['ea_date'].dt.year >= 2020]

#%%
# Build the event window data
# For each event, collect returns from -10 to +30 days relative to announcement

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

#%%
# Calculate average BHAR for each event day
avg_bhar = bhar_df[bhar_df['mcap_qnt']==0].groupby('event_day')['bhar'].mean().reset_index()
avg_bhar = avg_bhar.sort_values('event_day')

# Plot the average BHAR
plt.figure(figsize=(10, 6))
plt.plot(avg_bhar['event_day'], avg_bhar['bhar'], marker='o', markersize=4, linewidth=1.5)
plt.axhline(y=0, color='gray', linestyle='--', linewidth=0.8)
plt.axvline(x=0, color='red', linestyle='--', linewidth=0.8, label='Earnings Announcement')
plt.xlabel('Days Relative to Earnings Announcement')
plt.ylabel('Average Buy-and-Hold Abnormal Return (BHAR)')
plt.title('Average BHAR Around Earnings Announcements')
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()

# Calculate average BHAR for each event day
avg_bhar = bhar_df[bhar_df['mcap_qnt']>0].groupby('event_day')['bhar'].mean().reset_index()
avg_bhar = avg_bhar.sort_values('event_day')

# Plot the average BHAR
plt.figure(figsize=(10, 6))
plt.plot(avg_bhar['event_day'], avg_bhar['bhar'], marker='o', markersize=4, linewidth=1.5)
plt.axhline(y=0, color='gray', linestyle='--', linewidth=0.8)
plt.axvline(x=0, color='red', linestyle='--', linewidth=0.8, label='Earnings Announcement')
plt.xlabel('Days Relative to Earnings Announcement')
plt.ylabel('Average Buy-and-Hold Abnormal Return (BHAR)')
plt.title('Average BHAR Around Earnings Announcements')
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()

#%%
# Plot BHAR by earnings surprise quintile with 95% confidence intervals

# Calculate mean, standard error, and 95% CI for each quintile and event day
def calc_stats(group):
    n = len(group)
    mean = group['bhar'].mean()
    se = group['bhar'].std() / np.sqrt(n)
    ci_95 = stats.t.ppf(0.975, n - 1) * se if n > 1 else 0
    return pd.Series({'mean_bhar': mean, 'ci_95': ci_95, 'n': n})

bhar_by_quintile = bhar_df[bhar_df['mcap_qnt']==0].groupby(['sue_qnt', 'event_day']).apply(calc_stats).reset_index()

# Plot
plt.figure(figsize=(12, 7))
colors = plt.cm.RdYlGn(np.linspace(0.1, 0.9, 5))
quintile_labels = ['Q1 (Negative Surprise)', 'Q2', 'Q3', 'Q4', 'Q5 (Positive Surprise)']

for q in range(5):
    q_data = bhar_by_quintile[bhar_by_quintile['sue_qnt'] == q].sort_values('event_day')
    plt.plot(q_data['event_day'], q_data['mean_bhar'],
             color=colors[q], linewidth=1.5, label=quintile_labels[q])
    plt.fill_between(q_data['event_day'],
                     q_data['mean_bhar'] - q_data['ci_95'],
                     q_data['mean_bhar'] + q_data['ci_95'],
                     color=colors[q], alpha=0.2)

plt.axhline(y=0, color='gray', linestyle='--', linewidth=0.8)
plt.axvline(x=0, color='black', linestyle='--', linewidth=0.8)
plt.xlabel('Days Relative to Earnings Announcement')
plt.ylabel('Average Buy-and-Hold Abnormal Return (BHAR)')
plt.title('Average BHAR by Earnings Surprise Quintile')
plt.legend(loc='upper left')
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()

#%%