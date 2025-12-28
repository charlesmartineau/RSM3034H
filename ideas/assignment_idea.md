I want to design an assignment that forces student to learn python for financial data analysis. The assignment should include the following components:

1. Use yahoo finance to download historical stock price data for at least 10 different US companies with the risk-free rate (symbol: ^IRX) and S&P 500 (symbol: ^GSPC) data with at least 10 years of data.

2. Plot the price data using matplotlib to visualize trends and patterns. Make sure to include labels, titles, and legends.

3. Calculate key financial metrics such as daily returns, cumulative returns, and moving averages for each stock.

4. Go from from daily prices to monthly prices by resampling the data. Compute the monthly returns.

5. Perform a correlation analysis between the different stocks to understand how they move in relation to each other. Visualize the correlation matrix using a heatmap.

6. Which stocks outperformed the S&P 500 over the 10-year period? 
   1. First plot the cumulative returns of each stock against the S&P 500.
   2. Then identify and list the stocks that had higher cumulative returns than the S&P 500.

7. Make a table that summarizes the following for each stock:
   - Average monthly return
   - Monthly volatility (standard deviation of monthly returns)
   - Sharpe ratio (using the risk-free rate). Use excess returns for this calculation.
   - CAPM beta (using the S&P 500 as the market portfolio). Make sure you subtract the risk-free rate when calculating excess returns for both the stock and the market. Use linear regression to estimate beta.
   - Plot the security market line (SML) and mark each stock on the plot based on its beta and average excess return. Does the CAPM hold for these stocks?

8. Using monthly stock returns, for each stocks, test if past historical returns can predict future returns using a simple linear regression model. 
   1. Use lagged returns (e.g., previous month return) as the independent variable and current month return as the dependent variable.
   2. Report the regression coefficients, R-squared values, and p-values for each stock.
   3. Discuss whether there is any significant predictive power in past returns for future returns.

9. For one stock of your choice, implement an event study around a significant corporate event (e.g., earnings announcement, merger, etc.). 
   1. Identify the event date and collect stock price data for a window around the event (e.g., 30 days before and after).
   2. Calculate abnormal returns using a market model or the S&P 500 as the benchmark.
   3. Plot the cumulative abnormal returns (CAR) over the event window and discuss the impact of the event on stock price.

10. Show that when one goes from 1 to 10 stocks, the idiosyncratic risk decreases. This can be done by calculating and plotting the portfolio variance as more stocks are added to the portfolio. Assume equal weighting for simplicity. Use monthly data.

