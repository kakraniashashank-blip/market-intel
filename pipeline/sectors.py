import pandas as pd

# Standard NSE Sectoral Indices mapping (simplified for our RRG and aggregation)
# This mapping assigns key NSE tickers to standard sectors.
# For a full production build, we would scrape the index constituents daily from NSE.
# Here we define a baseline for the top ~500 stocks to cover the Nifty 500 universe.

SECTOR_MAP = {
    # IT
    'TCS': 'IT', 'INFY': 'IT', 'HCLTECH': 'IT', 'WIPRO': 'IT', 'TECHM': 'IT', 'LTIM': 'IT', 
    'PERSISTENT': 'IT', 'COFORGE': 'IT', 'MPHASIS': 'IT', 'KPITTECH': 'IT', 'TATAELXSI': 'IT',
    'OFSS': 'IT', 'CYIENT': 'IT', 'BSOFT': 'IT',
    
    # Banks
    'HDFCBANK': 'Banks', 'ICICIBANK': 'Banks', 'AXISBANK': 'Banks', 'KOTAKBANK': 'Banks', 
    'SBIN': 'Banks', 'INDUSINDBK': 'Banks', 'PNB': 'Banks', 'BANKBARODA': 'Banks',
    'FEDERALBNK': 'Banks', 'IDFCFIRSTB': 'Banks', 'AUBANK': 'Banks', 'CANBK': 'Banks',
    'UNIONBANK': 'Banks', 'YESBANK': 'Banks',
    
    # NBFC (Financial Services excluding banks)
    'BAJFINANCE': 'NBFC', 'BAJAJFINSV': 'NBFC', 'CHOLAFIN': 'NBFC', 'SHRIRAMFIN': 'NBFC',
    'MUTHOOTFIN': 'NBFC', 'MANAPPURAM': 'NBFC', 'RECLTD': 'NBFC', 'PFC': 'NBFC',
    'IREDA': 'NBFC', 'IRFC': 'NBFC', 'L&TFH': 'NBFC', 'LTF': 'NBFC', 'FEDFINA': 'NBFC',
    'SBICARD': 'NBFC', 'M&MFIN': 'NBFC', 'LICHSGFIN': 'NBFC', 'POONAWALLA': 'NBFC',
    
    # Auto
    'TATAMOTORS': 'Auto', 'M&M': 'Auto', 'MARUTI': 'Auto', 'BAJAJ-AUTO': 'Auto',
    'HEROMOTOCO': 'Auto', 'EICHERMOT': 'Auto', 'TVSMOTOR': 'Auto', 'ASHOKLEY': 'Auto',
    'ESCORTS': 'Auto', 'TIINDIA': 'Auto',
    
    # Auto Ancillary
    'BOSCHLTD': 'Auto Ancillary', 'MOTHERSON': 'Auto Ancillary', 'MRF': 'Auto Ancillary',
    'BALKRISIND': 'Auto Ancillary', 'APOLLOTYRE': 'Auto Ancillary', 'ENDURANCE': 'Auto Ancillary',
    'UNO MINDA': 'Auto Ancillary', 'SONACOMS': 'Auto Ancillary', 'CEATLTD': 'Auto Ancillary',
    
    # FMCG
    'ITC': 'FMCG', 'HINDUNILVR': 'FMCG', 'NESTLEIND': 'FMCG', 'BRITANNIA': 'FMCG',
    'TATACONSUM': 'FMCG', 'GODREJCP': 'FMCG', 'DABUR': 'FMCG', 'MARICO': 'FMCG',
    'COLPAL': 'FMCG', 'UBL': 'FMCG', 'MCDOWELL-N': 'FMCG', 'RADICO': 'FMCG',
    'VARROC': 'FMCG', 'VBL': 'FMCG',
    
    # Pharma
    'SUNPHARMA': 'Pharma', 'DIVISLAB': 'Pharma', 'CIPLA': 'Pharma', 'DRREDDY': 'Pharma',
    'APOLLOHOSP': 'Pharma', 'LUPIN': 'Pharma', 'TORNTPHARM': 'Pharma', 'ZYDUSLIFE': 'Pharma',
    'AUROPHARMA': 'Pharma', 'MAXHEALTH': 'Pharma', 'MANKIND': 'Pharma', 'BIOCON': 'Pharma',
    'GLENMARK': 'Pharma', 'SYNGENE': 'Pharma', 'NATCOPHARM': 'Pharma',
    
    # Metals
    'TATASTEEL': 'Metals', 'JSWSTEEL': 'Metals', 'HINDALCO': 'Metals', 'JINDALSTEL': 'Metals',
    'VEDL': 'Metals', 'COALINDIA': 'Metals', 'SAIL': 'Metals', 'NATIONALUM': 'Metals',
    'NMDC': 'Metals', 'HINDZINC': 'Metals', 'WELCORP': 'Metals', 'APLAPOLLO': 'Metals',
    
    # Capital Goods / Defence
    'L&T': 'Capital Goods', 'LT': 'Capital Goods', 'BEL': 'Capital Goods', 'HAL': 'Capital Goods',
    'SIEMENS': 'Capital Goods', 'ABB': 'Capital Goods', 'CGPOWER': 'Capital Goods',
    'BHEL': 'Capital Goods', 'CUMMINSIND': 'Capital Goods', 'POLYCAB': 'Capital Goods',
    'DIXON': 'Capital Goods', 'THERMAX': 'Capital Goods', 'AIAENG': 'Capital Goods',
    'SUZLON': 'Capital Goods', 'KAYNES': 'Capital Goods', 'ENGINERSIN': 'Capital Goods',
    
    # Oil & Gas
    'RELIANCE': 'Oil & Gas', 'ONGC': 'Oil & Gas', 'NTPC': 'Oil & Gas', 'POWERGRID': 'Oil & Gas',
    'TATAPOWER': 'Oil & Gas', 'ADANIPOWER': 'Oil & Gas', 'ADANIGREEN': 'Oil & Gas',
    'IOC': 'Oil & Gas', 'BPCL': 'Oil & Gas', 'HINDPETRO': 'Oil & Gas', 'GAIL': 'Oil & Gas',
    'PETRONET': 'Oil & Gas', 'IGL': 'Oil & Gas', 'MGL': 'Oil & Gas', 'OIL': 'Oil & Gas',
    'CHENNPETRO': 'Oil & Gas', 'MRPL': 'Oil & Gas',
    
    # Realty
    'DLF': 'Realty', 'MACROTECH': 'Realty', 'GODREJPROP': 'Realty', 'PRESTIGE': 'Realty',
    'OBEROIRLTY': 'Realty', 'PHOENIXLTD': 'Realty', 'BRIGADE': 'Realty', 'SOBHA': 'Realty',
    
    # Paper & Packaging
    'NRAIL': 'Paper', 'JKPAPER': 'Paper', 'WSTCSTPAPR': 'Paper', 'ANDHRAPAP': 'Paper',
    'TNPL': 'Paper', 'SESHAPAPER': 'Paper', 'EPL': 'Paper', 'UFLEX': 'Paper',
    
    # Chemicals / Agri
    'PIDILITIND': 'Chemicals', 'SRF': 'Chemicals', 'PIIND': 'Chemicals', 'TATACHEM': 'Chemicals',
    'DEEPAKNTR': 'Chemicals', 'NAVINFLUOR': 'Chemicals', 'AARTIIND': 'Chemicals',
    'UPL': 'Chemicals', 'COROMANDEL': 'Chemicals', 'CHAMBLFERT': 'Chemicals', 'FACT': 'Chemicals',
    
    # Consumer Durables
    'TITAN': 'Consumer Durables', 'ASIANPAINT': 'Consumer Durables', 'BERGEPAINT': 'Consumer Durables',
    'HAVELLS': 'Consumer Durables', 'VOLTAS': 'Consumer Durables', 'CROMPTON': 'Consumer Durables',
    'BATAINDIA': 'Consumer Durables', 'KALYANKJIL': 'Consumer Durables', 'PGEL': 'Consumer Durables',
    
    # Others
    'SVRL': 'Edible Oils', 'AWL': 'Edible Oils', 'PATANJALI': 'Edible Oils',
    'INDIGO': 'Aviation', 'ZOMATO': 'Internet', 'PAYTM': 'Internet', 'NYKAA': 'Internet',
    'PBFINTECH': 'Internet',
}

def get_sector(symbol):
    """Returns the sector for a given symbol, or 'Others' if not found."""
    return SECTOR_MAP.get(symbol, 'Others')

def get_all_sectors():
    """Returns a list of unique sectors."""
    return sorted(list(set(SECTOR_MAP.values())))
