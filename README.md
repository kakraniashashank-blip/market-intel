# MarketScope Analytics

An institutional-grade equity research platform designed to synthesize market microstructure data and fundamental business drivers into actionable tear sheets.

## Architecture

This project is entirely serverless, relying on a localized Python data pipeline and a static frontend. 

### 1. Data Pipeline (`/pipeline`)
- **Microstructure Engine:** Fetches daily price, volume, and delivery data from the NSE (National Stock Exchange).
- **Quantitative Scoring:** Computes rolling relative strength (RS), distance to moving averages, and Composite Sector Scores based on breadth and momentum.
- **Fundamental Engine (`primers.py`):** Integrates with the `yfinance` library for real-time valuation metrics (Market Cap, P/E, P/B, RoE) and calls the Gemini LLM API to auto-generate fundamental tear sheets based on SEC/Exchange filings and business summaries.

### 2. Frontend (`/frontend`)
- **Static Delivery:** `index.html` loads the generated `data.json` asynchronously, meaning the app can be hosted entirely on GitHub Pages without a backend server.
- **Institutional Design:** Strict adherence to professional typography (Garamond for analytical prose, Arial for tabular data).
- **Command Palette:** Quick entity search (Ctrl+K) enables instant navigation across the entire NSE universe.
- **Interactive RRG:** Relative Rotation Graphs visualizing sector momentum vs. ratio.

## Deployment & Usage

1. Run the Python pipeline locally to fetch the latest NSE Bhavcopy and generate AI primers.
   ```bash
   python pipeline/main.py
   python pipeline/primers.py
   ```
2. The output is compiled into `/frontend/data.json` and `/frontend/data/primers/`.
3. Open `index.html` (or push the `/frontend` directory to GitHub Pages) to interact with the updated daily data.

## Note on Implied Growth (Reverse DCF)
*A Reverse DCF module is currently in development to overlay market-implied growth rates (based on WACC and Terminal Growth assumptions) against historical delivery, providing a one-line valuation check for the tearsheets.*
