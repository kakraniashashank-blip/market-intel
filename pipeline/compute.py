import pandas as pd
import numpy as np
from datetime import datetime
import json
import os
from pathlib import Path

from bhavcopy import get_latest_data
from sectors import get_sector, get_all_sectors

def compute_moving_averages(df):
    """
    Computes 20, 50, 100, 200 DMAs. 
    Assumes df is sorted by DATE descending for each symbol.
    """
    # Sort by Date ascending for rolling calculations
    df = df.sort_values(['SYMBOL', 'TRADE_DATE'], ascending=[True, True])
    
    df['SMA_20'] = df.groupby('SYMBOL')['CLOSE_PRICE'].transform(lambda x: x.rolling(20, min_periods=10).mean())
    df['SMA_50'] = df.groupby('SYMBOL')['CLOSE_PRICE'].transform(lambda x: x.rolling(50, min_periods=25).mean())
    df['SMA_100'] = df.groupby('SYMBOL')['CLOSE_PRICE'].transform(lambda x: x.rolling(100, min_periods=50).mean())
    df['SMA_200'] = df.groupby('SYMBOL')['CLOSE_PRICE'].transform(lambda x: x.rolling(200, min_periods=100).mean())
    
    # Delivery Moving Averages
    df['DELIV_QTY_5D'] = df.groupby('SYMBOL')['DELIV_QTY'].transform(lambda x: x.rolling(5, min_periods=1).mean())
    df['DELIV_QTY_20D'] = df.groupby('SYMBOL')['DELIV_QTY'].transform(lambda x: x.rolling(20, min_periods=5).mean())
    
    return df

def compute_atr(df, period=14):
    """Computes Average True Range."""
    df = df.sort_values(['SYMBOL', 'TRADE_DATE'], ascending=[True, True])
    
    df['PREV_CLOSE_SHIFT'] = df.groupby('SYMBOL')['CLOSE_PRICE'].shift(1)
    
    df['TR1'] = df['HIGH_PRICE'] - df['LOW_PRICE']
    df['TR2'] = abs(df['HIGH_PRICE'] - df['PREV_CLOSE_SHIFT'])
    df['TR3'] = abs(df['LOW_PRICE'] - df['PREV_CLOSE_SHIFT'])
    
    df['TR'] = df[['TR1', 'TR2', 'TR3']].max(axis=1)
    df['ATR'] = df.groupby('SYMBOL')['TR'].transform(lambda x: x.rolling(period, min_periods=1).mean())
    df['ATR_PCT'] = (df['ATR'] / df['CLOSE_PRICE']) * 100
    
    return df

def compute_relative_strength(df, index_df=None):
    """
    Computes RS vs Nifty 500 (or a proxy). 
    Since we don't have Nifty 500 directly in EQ bhavcopy, we'll use a broad market proxy 
    (e.g., median return of all stocks) if index_df is None.
    """
    df = df.sort_values('TRADE_DATE')
    dates = df['TRADE_DATE'].unique()
    
    # Calculate market proxy: daily median return
    daily_returns = df.groupby('TRADE_DATE')['CLOSE_PRICE'].mean().pct_change().fillna(0)
    market_index = (1 + daily_returns).cumprod() * 100
    
    # Create market df
    market_df = pd.DataFrame({'TRADE_DATE': market_index.index, 'MARKET_PX': market_index.values})
    
    df = pd.merge(df, market_df, on='TRADE_DATE', how='left')
    df = df.sort_values(['SYMBOL', 'TRADE_DATE'])
    
    df['RS_RATIO_RAW'] = df['CLOSE_PRICE'] / df['MARKET_PX']
    df['RS_RATIO_SMA52'] = df.groupby('SYMBOL')['RS_RATIO_RAW'].transform(lambda x: x.rolling(250, min_periods=100).mean())
    
    # RS Ratio (Normalized to 100)
    df['RS_RATIO'] = 100 * (df['RS_RATIO_RAW'] / df['RS_RATIO_SMA52'])
    
    # RS Momentum (Rate of change of RS Ratio)
    df['RS_MOMENTUM'] = 100 * (df['RS_RATIO'] / df.groupby('SYMBOL')['RS_RATIO'].transform(lambda x: x.rolling(10).mean()))
    
    # Compute 1M, 3M, 6M returns for composite scoring
    df['RET_1M'] = df.groupby('SYMBOL')['CLOSE_PRICE'].pct_change(periods=21) * 100
    df['RET_3M'] = df.groupby('SYMBOL')['CLOSE_PRICE'].pct_change(periods=63) * 100
    df['RET_6M'] = df.groupby('SYMBOL')['CLOSE_PRICE'].pct_change(periods=126) * 100
    
    return df

def rank_percentiles(df_latest):
    """Ranks stocks into percentiles based on returns."""
    for col in ['RET_1M', 'RET_3M', 'RET_6M']:
        if col in df_latest.columns:
            df_latest[f'RS_{col[-2:]}'] = df_latest[col].rank(pct=True) * 100
    
    return df_latest

def compute_sector_metrics(df_latest):
    """Computes sector level aggregated metrics."""
    # Add sector column
    df_latest['SECTOR'] = df_latest['SYMBOL'].apply(get_sector)
    
    # Breadth: % > 50 DMA
    df_latest['ABOVE_50D'] = (df_latest['CLOSE_PRICE'] > df_latest['SMA_50']).astype(int)
    
    sector_grouped = df_latest.groupby('SECTOR')
    
    sector_metrics = pd.DataFrame({
        'BREADTH_50D': sector_grouped['ABOVE_50D'].mean() * 100,
        'AVG_RS_3M': sector_grouped['RS_3M'].mean(),
        'AVG_RS_RATIO': sector_grouped['RS_RATIO'].mean(),
        'AVG_RS_MOM': sector_grouped['RS_MOMENTUM'].mean(),
        'TOTAL_TURNOVER': sector_grouped['TURNOVER_LACS'].sum()
    }).reset_index()
    
    # Calculate composite score (0-100)
    sector_metrics['COMPOSITE'] = (sector_metrics['BREADTH_50D'] * 0.4 + 
                                  sector_metrics['AVG_RS_3M'] * 0.4 + 
                                  sector_metrics['AVG_RS_RATIO'] * 0.2).rank(pct=True) * 100
                                  
    sector_metrics = sector_metrics.sort_values('COMPOSITE', ascending=False)
    return sector_metrics

def compute_market_breadth(df):
    """Computes daily market breadth metrics."""
    dates = sorted(df['TRADE_DATE'].unique())
    breadth_data = []
    
    for d in dates[-20:]:  # Last 20 days for chart/trend
        day_df = df[df['TRADE_DATE'] == d]
        
        advances = len(day_df[day_df['CLOSE_PRICE'] > day_df['PREV_CLOSE']])
        declines = len(day_df[day_df['CLOSE_PRICE'] < day_df['PREV_CLOSE']])
        
        # Delivery weighted A/D
        adv_deliv = day_df[day_df['CLOSE_PRICE'] > day_df['PREV_CLOSE']]['DELIV_QTY'].sum()
        dec_deliv = day_df[day_df['CLOSE_PRICE'] < day_df['PREV_CLOSE']]['DELIV_QTY'].sum()
        
        ad_ratio_headcount = advances / declines if declines > 0 else advances
        ad_ratio_deliv = adv_deliv / dec_deliv if dec_deliv > 0 else adv_deliv
        
        above_50 = (day_df['CLOSE_PRICE'] > day_df['SMA_50']).mean() * 100
        above_200 = (day_df['CLOSE_PRICE'] > day_df['SMA_200']).mean() * 100
        
        breadth_data.append({
            'DATE': d,
            'ADVANCES': advances,
            'DECLINES': declines,
            'AD_RATIO': round(ad_ratio_headcount, 2),
            'AD_RATIO_DELIV': round(ad_ratio_deliv, 2),
            'ABOVE_50D': round(above_50, 1),
            'ABOVE_200D': round(above_200, 1)
        })
        
    return pd.DataFrame(breadth_data)

def generate_json_payload():
    """Main orchestrator to compute and dump data.json"""
    print("Loading data...")
    # Load 260 days (approx 1 year) if available
    df = get_latest_data(260)
    
    if df.empty:
        print("No data available. Run bhavcopy.py first.")
        return
        
    print(f"Loaded {len(df)} rows. Computing metrics...")
    
    df = compute_moving_averages(df)
    df = compute_atr(df)
    df = compute_relative_strength(df)
    
    latest_date = df['TRADE_DATE'].max()
    df_latest = df[df['TRADE_DATE'] == latest_date].copy()
    
    df_latest = rank_percentiles(df_latest)
    
    print("Computing sector metrics...")
    sector_df = compute_sector_metrics(df_latest)
    
    print("Computing market breadth...")
    breadth_df = compute_market_breadth(df)
    
    # Format data for JSON output
    output = {
        'metadata': {
            'last_updated': latest_date,
            'total_stocks': len(df_latest)
        },
        'market_health': {
            'breadth_trend': breadth_df.to_dict('records')
        },
        'sectors': sector_df.to_dict('records'),
        'stocks': {}
    }
    
    # Prepare top stocks dictionary for easy lookup
    df_latest['SECTOR'] = df_latest['SYMBOL'].apply(get_sector)
    
    for _, row in df_latest.iterrows():
        # Only include top stocks by turnover or specific watchlist to keep JSON small
        if row['TURNOVER_LACS'] > 50 or row['SECTOR'] != 'Others':
            output['stocks'][row['SYMBOL']] = {
                'px': round(row['CLOSE_PRICE'], 2),
                'chg_pct': round((row['CLOSE_PRICE']/row['PREV_CLOSE'] - 1)*100, 2),
                'sector': row['SECTOR'],
                'rs_1m': round(row.get('RS_1M', 0), 0),
                'rs_3m': round(row.get('RS_3M', 0), 0),
                'vs_50d': round((row['CLOSE_PRICE']/row['SMA_50'] - 1)*100, 1) if pd.notna(row['SMA_50']) else None,
                'atr_pct': round(row['ATR_PCT'], 1) if pd.notna(row['ATR_PCT']) else None,
                'deliv_pct': round(row['DELIV_PER'], 1) if pd.notna(row['DELIV_PER']) else None
            }
            
    # Save to frontend directory
    frontend_dir = Path(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend'))
    frontend_dir.mkdir(parents=True, exist_ok=True)
    
    with open(frontend_dir / 'data.json', 'w') as f:
        json.dump(output, f)
        
    print(f"Data saved to {frontend_dir / 'data.json'}")

    top_5_tickers = df_latest.nlargest(5, 'TURNOVER_LACS')['SYMBOL'].tolist()
    return top_5_tickers

if __name__ == "__main__":
    generate_json_payload()
