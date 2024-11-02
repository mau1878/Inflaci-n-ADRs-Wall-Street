import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# Load U.S. CPI data
@st.cache_data
def load_inflation_data():
    # Load CPI data from the uploaded file
    inflation_data = pd.read_csv('CPIAUCSL.csv', parse_dates=['DATE'])
    inflation_data.set_index('DATE', inplace=True)
    inflation_data.rename(columns={'CPIAUCSL': 'CPI'}, inplace=True)
    return inflation_data

# Interpolates CPI data for daily values
def interpolate_cpi(cpi_data):
    # Resample CPI monthly data to daily and interpolate for smooth transition
    daily_cpi = cpi_data.resample('D').interpolate(method='linear')
    return daily_cpi

# Fetch stock data from yfinance
def get_stock_data(ticker, start_date, end_date):
    stock_data = yf.download(ticker, start=start_date, end=end_date)
    return stock_data['Adj Close']

# Align stock and CPI data on dates and adjust stock prices for inflation
def adjust_for_inflation(stock_data, cpi_data):
    # Normalize CPI to 1 at the latest date for easier adjustment
    cpi_data = cpi_data / cpi_data.iloc[-1]

    # Convert stock_data index to UTC if needed
    if stock_data.index.tz is None:
        stock_data.index = stock_data.index.tz_localize("UTC")
    else:
        stock_data.index = stock_data.index.tz_convert("UTC")

    # Reindex CPI data to align with the stock data index (date range)
    cpi_data = cpi_data.reindex(stock_data.index, method='ffill')
    
    # Adjust stock prices for inflation
    adjusted_prices = stock_data / cpi_data['CPI']
    return adjusted_prices



# Streamlit app
st.title("Stock Price Adjustment for U.S. Inflation")
st.write("Adjust stock prices by interpolated U.S. inflation data to smooth out monthly jumps.")

# Inputs
ticker = st.text_input("Enter Stock Ticker (e.g., AAPL):", value="AAPL").upper()
start_date = st.date_input("Start Date:", value=datetime(2010, 1, 1))
end_date = st.date_input("End Date:", value=datetime.today())

# Load data and process
if ticker:
    inflation_data = load_inflation_data()
    daily_cpi = interpolate_cpi(inflation_data)
    
    # Fetch and adjust stock data
    stock_data = get_stock_data(ticker, start_date, end_date)
    daily_cpi = daily_cpi.loc[start_date:end_date]
    adjusted_stock_data = adjust_for_inflation(stock_data, daily_cpi)
    
    # Plot original and adjusted stock prices
    st.write(f"Adjusted stock price of {ticker} for U.S. inflation:")
    st.line_chart(pd.DataFrame({
        'Original Price': stock_data,
        'Inflation Adjusted Price': adjusted_stock_data
    }))
