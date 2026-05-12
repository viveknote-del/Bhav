"""NIFTY 50 constituents as the starter universe.

Bundled rather than fetched: NSE doesn't have a stable public API for the
constituent list, and the index changes ~twice per year. Refresh manually
via `make refresh-universe` (Step 1+) or hardcode updates here.

Names + sectors are sourced statically; market_cap is filled at refresh time
via the market_data provider.
"""

NIFTY_50: list[dict] = [
    {"symbol": "RELIANCE.NS",   "name": "Reliance Industries",          "sector": "Energy"},
    {"symbol": "TCS.NS",        "name": "Tata Consultancy Services",    "sector": "Information Technology"},
    {"symbol": "HDFCBANK.NS",   "name": "HDFC Bank",                    "sector": "Financial Services"},
    {"symbol": "BHARTIARTL.NS", "name": "Bharti Airtel",                "sector": "Telecommunication"},
    {"symbol": "ICICIBANK.NS",  "name": "ICICI Bank",                   "sector": "Financial Services"},
    {"symbol": "INFY.NS",       "name": "Infosys",                      "sector": "Information Technology"},
    {"symbol": "SBIN.NS",       "name": "State Bank of India",          "sector": "Financial Services"},
    {"symbol": "LT.NS",         "name": "Larsen & Toubro",              "sector": "Construction"},
    {"symbol": "ITC.NS",        "name": "ITC",                          "sector": "Consumer Goods"},
    {"symbol": "HINDUNILVR.NS", "name": "Hindustan Unilever",           "sector": "Consumer Goods"},
    {"symbol": "BAJFINANCE.NS", "name": "Bajaj Finance",                "sector": "Financial Services"},
    {"symbol": "KOTAKBANK.NS",  "name": "Kotak Mahindra Bank",          "sector": "Financial Services"},
    {"symbol": "MARUTI.NS",     "name": "Maruti Suzuki India",          "sector": "Automobile"},
    {"symbol": "AXISBANK.NS",   "name": "Axis Bank",                    "sector": "Financial Services"},
    {"symbol": "M&M.NS",        "name": "Mahindra & Mahindra",          "sector": "Automobile"},
    {"symbol": "SUNPHARMA.NS",  "name": "Sun Pharmaceutical",           "sector": "Pharma"},
    {"symbol": "NTPC.NS",       "name": "NTPC",                         "sector": "Energy"},
    {"symbol": "HCLTECH.NS",    "name": "HCL Technologies",             "sector": "Information Technology"},
    {"symbol": "TITAN.NS",      "name": "Titan Company",                "sector": "Consumer Goods"},
    {"symbol": "ULTRACEMCO.NS", "name": "UltraTech Cement",             "sector": "Cement"},
    {"symbol": "ASIANPAINT.NS", "name": "Asian Paints",                 "sector": "Consumer Goods"},
    {"symbol": "BAJAJFINSV.NS", "name": "Bajaj Finserv",                "sector": "Financial Services"},
    {"symbol": "ONGC.NS",       "name": "Oil & Natural Gas Corporation","sector": "Energy"},
    {"symbol": "ADANIENT.NS",   "name": "Adani Enterprises",            "sector": "Diversified"},
    {"symbol": "WIPRO.NS",      "name": "Wipro",                        "sector": "Information Technology"},
    {"symbol": "POWERGRID.NS",  "name": "Power Grid Corporation",       "sector": "Energy"},
    {"symbol": "JSWSTEEL.NS",   "name": "JSW Steel",                    "sector": "Metals"},
    {"symbol": "TATAMOTORS.NS", "name": "Tata Motors",                  "sector": "Automobile"},
    {"symbol": "COALINDIA.NS",  "name": "Coal India",                   "sector": "Energy"},
    {"symbol": "ADANIPORTS.NS", "name": "Adani Ports & SEZ",            "sector": "Services"},
    {"symbol": "NESTLEIND.NS",  "name": "Nestle India",                 "sector": "Consumer Goods"},
    {"symbol": "TATASTEEL.NS",  "name": "Tata Steel",                   "sector": "Metals"},
    {"symbol": "BAJAJ-AUTO.NS", "name": "Bajaj Auto",                   "sector": "Automobile"},
    {"symbol": "GRASIM.NS",     "name": "Grasim Industries",            "sector": "Cement"},
    {"symbol": "HINDALCO.NS",   "name": "Hindalco Industries",          "sector": "Metals"},
    {"symbol": "DRREDDY.NS",    "name": "Dr Reddy's Laboratories",      "sector": "Pharma"},
    {"symbol": "CIPLA.NS",      "name": "Cipla",                        "sector": "Pharma"},
    {"symbol": "BRITANNIA.NS",  "name": "Britannia Industries",         "sector": "Consumer Goods"},
    {"symbol": "TECHM.NS",      "name": "Tech Mahindra",                "sector": "Information Technology"},
    {"symbol": "EICHERMOT.NS",  "name": "Eicher Motors",                "sector": "Automobile"},
    {"symbol": "INDUSINDBK.NS", "name": "IndusInd Bank",                "sector": "Financial Services"},
    {"symbol": "TATACONSUM.NS", "name": "Tata Consumer Products",       "sector": "Consumer Goods"},
    {"symbol": "APOLLOHOSP.NS", "name": "Apollo Hospitals",             "sector": "Healthcare"},
    {"symbol": "DIVISLAB.NS",   "name": "Divi's Laboratories",          "sector": "Pharma"},
    {"symbol": "HEROMOTOCO.NS", "name": "Hero MotoCorp",                "sector": "Automobile"},
    {"symbol": "BPCL.NS",       "name": "Bharat Petroleum",             "sector": "Energy"},
    {"symbol": "SHRIRAMFIN.NS", "name": "Shriram Finance",              "sector": "Financial Services"},
    {"symbol": "SBILIFE.NS",    "name": "SBI Life Insurance",           "sector": "Financial Services"},
    {"symbol": "HDFCLIFE.NS",   "name": "HDFC Life Insurance",          "sector": "Financial Services"},
    {"symbol": "LTIM.NS",       "name": "LTIMindtree",                  "sector": "Information Technology"},
]
