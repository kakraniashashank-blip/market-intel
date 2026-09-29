import os
import json
import time
from pathlib import Path
import yfinance as yf
import google.generativeai as genai
import winreg

# Setup API Key
api_key = os.environ.get('GEMINI_API_KEY')
if not api_key:
    try:
        api_key = winreg.QueryValueEx(winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment'), 'GEMINI_API_KEY')[0]
    except Exception:
        pass

if not api_key:
    print("WARNING: GEMINI_API_KEY not found. Primers will not be generated.")
else:
    genai.configure(api_key=api_key)

# We use a standard available model
model = genai.GenerativeModel('gemini-3.1-pro-preview')

PROMPT_TEMPLATE = """
You are a senior equity research analyst at an institutional bank.
Write a crisp, professional fundamental synthesis for the Indian company '{company_name}' ({ticker}).
Use the following business summary from Yahoo Finance as your baseline context:
---
{summary}
---

Your output must be formatted as HTML (without ```html wrappers) and adhere exactly to this structure:

<h3 style="margin-top:0;">Business Overview</h3>
<p class="prose">
[Explain what the business actually does, how it makes money, and its core margin engine. Assume the reader is smart but has zero prior knowledge of this specific company. 3-4 sentences maximum.]
</p>

<h3>Key Growth & Margin Drivers</h3>
<p class="prose">
[Bullet points (using <ul> and <li>) listing 3 to 4 specific mechanisms that drive this company's earnings. Don't just give labels like "Rising Demand". Explain the mechanism, e.g., "Operating Leverage: As capacity utilization crosses 70%, fixed cost absorption disproportionately drops to the bottom line."]
</p>

<h3>The Core Tension / Risk</h3>
<p class="prose">
[What is the single biggest structural conflict, risk, or push-and-pull dynamic in this business right now? e.g., "Growth vs Asset Quality" or "Raw Material Volatility". 2-3 sentences.]
</p>

<h3>Triggers to Watch</h3>
<p class="prose">
[1-2 specific, falsifiable events that would materially change the valuation or earnings trajectory.]
</p>

Keep the tone extremely professional, dense with insight, and free of fluff or retail trading jargon.
"""

def get_yfinance_data(symbol):
    """Fetches valuation data and business summary from yfinance."""
    try:
        t = yf.Ticker(f"{symbol}.NS") if not symbol.endswith('.NS') and not symbol.endswith('.BO') else yf.Ticker(symbol)
        
        # Some stocks (like SVRL) might be BSE only.
        if 'longBusinessSummary' not in t.info:
            if not symbol.endswith('.BO') and not symbol.endswith('.NS'):
                t = yf.Ticker(f"{symbol}.BO")
                
        info = t.info
        
        return {
            'mcap': info.get('marketCap'),
            'pe': info.get('trailingPE') or info.get('forwardPE'),
            'pb': info.get('priceToBook'),
            'roe': info.get('returnOnEquity'),
            'summary': info.get('longBusinessSummary', 'Business summary not available.'),
            'shortName': info.get('shortName', symbol)
        }
    except Exception as e:
        print(f"Error fetching {symbol} from yfinance: {e}")
        return None

def generate_primer(symbol):
    print(f"Generating primer for {symbol}...")
    yf_data = get_yfinance_data(symbol)
    
    if not yf_data:
        return None
        
    # Generate LLM content
    html_content = ""
    if api_key and yf_data['summary'] != 'Business summary not available.':
        prompt = PROMPT_TEMPLATE.format(
            company_name=yf_data['shortName'], 
            ticker=symbol, 
            summary=yf_data['summary']
        )
        try:
            response = model.generate_content(prompt)
            html_content = response.text.replace('```html', '').replace('```', '').strip()
        except Exception as e:
            print(f"Gemini API error for {symbol}: {e}")
            if '429' in str(e) or 'quota' in str(e).lower():
                html_content = "<p class='prose'><em>Note: Automated LLM synthesis is temporarily paused due to API quota limits. Valuation metrics above are real-time.</em></p>"
            else:
                html_content = f"<p class='prose'><em>Synthesis currently unavailable ({str(e)[:50]}).</em></p>"
    else:
        html_content = "<p class='prose'>No fundamental text available to synthesize.</p>"

    primer_data = {
        'symbol': symbol,
        'company_name': yf_data['shortName'],
        'valuation': {
            'mcap_cr': round(yf_data['mcap'] / 10000000, 1) if yf_data['mcap'] else None, # Convert to Crores
            'pe': round(yf_data['pe'], 2) if yf_data['pe'] else None,
            'pb': round(yf_data['pb'], 2) if yf_data['pb'] else None,
            'roe_pct': round(yf_data['roe'] * 100, 2) if yf_data['roe'] else None
        },
        'html': html_content
    }
    
    return primer_data

def build_primers(tickers):
    output_dir = Path(__file__).parent.parent / 'frontend' / 'data' / 'primers'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results = {}
    for ticker in tickers:
        data = generate_primer(ticker)
        if data:
            results[ticker] = data
            with open(output_dir / f"{ticker}.json", 'w') as f:
                json.dump(data, f, indent=2)
            
            if 'LLM synthesis is temporarily paused' in data['html']:
                time.sleep(1)
            else:
                print(f"Sleeping for 20 seconds to respect API rate limits...")
                time.sleep(20)
        else:
            time.sleep(1)
        
    return results

if __name__ == "__main__":
    test_tickers = ['FEDFINA', 'SVRL', 'NRAIL', 'RELIANCE', 'HDFCBANK']
    build_primers(test_tickers)
