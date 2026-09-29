import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import time
import io

DATA_DIR = Path(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'daily'))

def get_session():
    """Returns a requests Session with NSE cookies configured."""
    s = requests.Session()
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br'
    })
    
    # Hit homepage first to get cookies
    try:
        s.get('https://www.nseindia.com', timeout=10)
    except Exception as e:
        print(f"Warning: Could not fetch NSE homepage: {e}")
    return s

def fetch_bhavcopy_for_date(date_obj, session=None):
    """
    Fetches bhavcopy for a specific date object.
    Returns a pandas DataFrame or None if not available (e.g. holiday/weekend).
    """
    if session is None:
        session = get_session()
        
    date_str = date_obj.strftime("%d%m%Y")
    url = f"https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{date_str}.csv"
    
    try:
        # Rate limit friendly
        time.sleep(1.5)
        response = session.get(url, timeout=15)
        
        if response.status_code == 200:
            # Clean up the CSV (NSE files often have trailing spaces in column names)
            df = pd.read_csv(io.StringIO(response.text))
            df.columns = df.columns.str.strip()
            
            # Filter to EQ series only
            if 'SERIES' in df.columns:
                df = df[df['SERIES'].str.strip() == 'EQ'].copy()
                
            # Clean up string columns
            for col in df.select_dtypes(include=['object']):
                df[col] = df[col].str.strip()
                
            # Add proper date column (useful when concatenating)
            df['TRADE_DATE'] = date_obj.strftime("%Y-%m-%d")
            
            # Type casting for key columns
            numeric_cols = ['PREV_CLOSE', 'OPEN_PRICE', 'HIGH_PRICE', 'LOW_PRICE', 
                            'LAST_PRICE', 'CLOSE_PRICE', 'AVG_PRICE', 'TTL_TRD_QNTY',
                            'TURNOVER_LACS', 'NO_OF_TRADES', 'DELIV_QTY', 'DELIV_PER']
            
            for col in numeric_cols:
                if col in df.columns:
                    # Handle possible '-' or other missing values in NSE files
                    df[col] = pd.to_numeric(df[col].replace(['-', ' - '], pd.NA), errors='coerce')
                    
            return df
        elif response.status_code == 404:
            return None # Holiday or weekend
        else:
            print(f"Failed to fetch {date_str}: HTTP {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Error fetching {date_str}: {e}")
        return None

def backfill(days_back=30):
    """
    Backfills data for the last N days.
    """
    print(f"Starting backfill for last {days_back} days...")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    session = get_session()
    today = datetime.now()
    
    success_count = 0
    
    for i in range(days_back):
        current_date = today - timedelta(days=i)
        
        # Skip weekends automatically
        if current_date.weekday() >= 5: 
            continue
            
        file_path = DATA_DIR / f"{current_date.strftime('%Y-%m-%d')}.parquet"
        
        if file_path.exists():
            continue
            
        print(f"Fetching data for {current_date.strftime('%Y-%m-%d')}...")
        df = fetch_bhavcopy_for_date(current_date, session)
        
        if df is not None and not df.empty:
            df.to_parquet(file_path, index=False)
            success_count += 1
            print(f"  -> Saved {len(df)} EQ records.")
        else:
            print(f"  -> No data (Likely a holiday)")
            
    print(f"Backfill complete. Fetched {success_count} new days.")

def get_latest_data(lookback_days=100):
    """
    Loads the last N trading days of data from parquet files into a single DataFrame.
    """
    files = sorted(list(DATA_DIR.glob("*.parquet")), reverse=True)
    if not files:
        return pd.DataFrame()
        
    dfs = []
    for f in files[:lookback_days]:
        dfs.append(pd.read_parquet(f))
        
    if not dfs:
        return pd.DataFrame()
        
    return pd.concat(dfs, ignore_index=True)

if __name__ == "__main__":
    backfill(30)
