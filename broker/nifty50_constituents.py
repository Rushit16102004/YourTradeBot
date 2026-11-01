"""
broker/nifty50_constituents.py - Top 50 Constituent Stocks of NIFTY 50 Index.
Provides official NSE symbols, Yahoo Finance tickers, and Angel One symbol tokens.
"""
from typing import Dict, List

# Official 50 constituent stocks of the NIFTY 50 Index
NIFTY_50_STOCKS: List[Dict[str, str]] = [
    {"symbol": "RELIANCE", "yf_ticker": "RELIANCE.NS", "token": "2885", "sector": "Energy"},
    {"symbol": "HDFCBANK", "yf_ticker": "HDFCBANK.NS", "token": "1333", "sector": "Financial Services"},
    {"symbol": "ICICIBANK", "yf_ticker": "ICICIBANK.NS", "token": "4963", "sector": "Financial Services"},
    {"symbol": "INFY", "yf_ticker": "INFY.NS", "token": "1594", "sector": "IT"},
    {"symbol": "ITC", "yf_ticker": "ITC.NS", "token": "1660", "sector": "Consumer Goods"},
    {"symbol": "TCS", "yf_ticker": "TCS.NS", "token": "11536", "sector": "IT"},
    {"symbol": "LT", "yf_ticker": "LT.NS", "token": "11483", "sector": "Construction"},
    {"symbol": "BHARTIARTL", "yf_ticker": "BHARTIARTL.NS", "token": "10604", "sector": "Telecommunication"},
    {"symbol": "AXISBANK", "yf_ticker": "AXISBANK.NS", "token": "5900", "sector": "Financial Services"},
    {"symbol": "SBIN", "yf_ticker": "SBIN.NS", "token": "3045", "sector": "Financial Services"},
    {"symbol": "KOTAKBANK", "yf_ticker": "KOTAKBANK.NS", "token": "1922", "sector": "Financial Services"},
    {"symbol": "HINDUNILVR", "yf_ticker": "HINDUNILVR.NS", "token": "1394", "sector": "Consumer Goods"},
    {"symbol": "BAJFINANCE", "yf_ticker": "BAJFINANCE.NS", "token": "317", "sector": "Financial Services"},
    {"symbol": "M&M", "yf_ticker": "M&M.NS", "token": "2031", "sector": "Automobile"},
    {"symbol": "MARUTI", "yf_ticker": "MARUTI.NS", "token": "10999", "sector": "Automobile"},
    {"symbol": "SUNPHARMA", "yf_ticker": "SUNPHARMA.NS", "token": "3351", "sector": "Pharma"},
    {"symbol": "TITAN", "yf_ticker": "TITAN.NS", "token": "3506", "sector": "Consumer Durables"},
    {"symbol": "TATASTEEL", "yf_ticker": "TATASTEEL.NS", "token": "3499", "sector": "Metals"},
    {"symbol": "POWERGRID", "yf_ticker": "POWERGRID.NS", "token": "14977", "sector": "Power"},
    {"symbol": "NTPC", "yf_ticker": "NTPC.NS", "token": "11630", "sector": "Power"},
    {"symbol": "ASIANPAINT", "yf_ticker": "ASIANPAINT.NS", "token": "236", "sector": "Consumer Durables"},
    {"symbol": "BAJAJFINSV", "yf_ticker": "BAJAJFINSV.NS", "token": "16675", "sector": "Financial Services"},
    {"symbol": "ULTRACEMCO", "yf_ticker": "ULTRACEMCO.NS", "token": "11532", "sector": "Construction Materials"},
    {"symbol": "ADANIENT", "yf_ticker": "ADANIENT.NS", "token": "25", "sector": "Metals & Mining"},
    {"symbol": "ADANIPORTS", "yf_ticker": "ADANIPORTS.NS", "token": "15083", "sector": "Services"},
    {"symbol": "COALINDIA", "yf_ticker": "COALINDIA.NS", "token": "20374", "sector": "Oil Gas & Fuels"},
    {"symbol": "ONGC", "yf_ticker": "ONGC.NS", "token": "2475", "sector": "Oil Gas & Fuels"},
    {"symbol": "JSWSTEEL", "yf_ticker": "JSWSTEEL.NS", "token": "11723", "sector": "Metals"},
    {"symbol": "GRASIM", "yf_ticker": "GRASIM.NS", "token": "1232", "sector": "Construction Materials"},
    {"symbol": "HINDALCO", "yf_ticker": "HINDALCO.NS", "token": "1363", "sector": "Metals"},
    {"symbol": "TECHM", "yf_ticker": "TECHM.NS", "token": "13538", "sector": "IT"},
    {"symbol": "WIPRO", "yf_ticker": "WIPRO.NS", "token": "3787", "sector": "IT"},
    {"symbol": "HCLTECH", "yf_ticker": "HCLTECH.NS", "token": "7229", "sector": "IT"},
    {"symbol": "CIPLA", "yf_ticker": "CIPLA.NS", "token": "694", "sector": "Pharma"},
    {"symbol": "DRREDDY", "yf_ticker": "DRREDDY.NS", "token": "881", "sector": "Pharma"},
    {"symbol": "APOLLOHOSP", "yf_ticker": "APOLLOHOSP.NS", "token": "157", "sector": "Healthcare"},
    {"symbol": "DIVISLAB", "yf_ticker": "DIVISLAB.NS", "token": "10940", "sector": "Pharma"},
    {"symbol": "EICHERMOT", "yf_ticker": "EICHERMOT.NS", "token": "910", "sector": "Automobile"},
    {"symbol": "HEROMOTOCO", "yf_ticker": "HEROMOTOCO.NS", "token": "1348", "sector": "Automobile"},
    {"symbol": "BAJAJ-AUTO", "yf_ticker": "BAJAJ-AUTO.NS", "token": "16669", "sector": "Automobile"},
    {"symbol": "BPCL", "yf_ticker": "BPCL.NS", "token": "526", "sector": "Oil Gas & Fuels"},
    {"symbol": "TATACONSUM", "yf_ticker": "TATACONSUM.NS", "token": "3432", "sector": "Consumer Goods"},
    {"symbol": "BRITANNIA", "yf_ticker": "BRITANNIA.NS", "token": "547", "sector": "Consumer Goods"},
    {"symbol": "NESTLEIND", "yf_ticker": "NESTLEIND.NS", "token": "17963", "sector": "Consumer Goods"},
    {"symbol": "SBILIFE", "yf_ticker": "SBILIFE.NS", "token": "21808", "sector": "Financial Services"},
    {"symbol": "HDFCLIFE", "yf_ticker": "HDFCLIFE.NS", "token": "467", "sector": "Financial Services"},
    {"symbol": "BEL", "yf_ticker": "BEL.NS", "token": "383", "sector": "Capital Goods"},
    {"symbol": "SHRIRAMFIN", "yf_ticker": "SHRIRAMFIN.NS", "token": "4306", "sector": "Financial Services"},
    {"symbol": "TRENT", "yf_ticker": "TRENT.NS", "token": "1964", "sector": "Consumer Services"},
    {"symbol": "INDUSINDBK", "yf_ticker": "INDUSINDBK.NS", "token": "5258", "sector": "Financial Services"},
]


def get_all_nifty50_symbols() -> List[str]:
    """Returns list of plain symbols, e.g. ['RELIANCE', 'HDFCBANK', ...]."""
    return [s["symbol"] for s in NIFTY_50_STOCKS]


def get_all_yf_tickers() -> List[str]:
    """Returns list of Yahoo Finance tickers, e.g. ['RELIANCE.NS', 'HDFCBANK.NS', ...]."""
    return [s["yf_ticker"] for s in NIFTY_50_STOCKS]


def get_all_tokens() -> List[str]:
    """Returns list of Angel One symbol tokens."""
    return [s["token"] for s in NIFTY_50_STOCKS]
