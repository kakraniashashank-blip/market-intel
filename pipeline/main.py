import os
from pathlib import Path
from bhavcopy import backfill
from compute import generate_json_payload

def main():
    print("--- Market Intelligence Pipeline ---")
    
    # 1. Fetch today's data (backfill handles skipping weekends/existing files)
    # We do a 5-day check just to ensure we catch up if the script didn't run for a few days
    print("\n[1/3] Updating NSE data...")
    backfill(5) 
    
    # 2. Compute metrics and generate JSON payload for frontend
    print("\n[2/3] Computing analytics and generating data.json...")
    generate_json_payload()
    
    # 3. Primer generation (Phase 3 placeholder)
    print("\n[3/3] LLM Primer Generation...")
    print("Skipping (To be implemented in Phase 3)")
    
    print("\nPipeline Complete!")

if __name__ == "__main__":
    main()
