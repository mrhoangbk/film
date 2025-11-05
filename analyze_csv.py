#!/usr/bin/env python3
import os
import pandas as pd
import glob

def analyze_csv_files():
    csv_files = glob.glob("data/ml-20m/*.csv")
    
    for csv_file in csv_files:
        print(f"\n{'='*60}")
        print(f"File: {csv_file}")
        print(f"{'='*60}")
        
        try:
            # Read first 10 rows
            df = pd.read_csv(csv_file, nrows=10)
            print(f"Shape: {df.shape}")
            print(f"Columns: {list(df.columns)}")
            print("\nFirst 10 rows:")
            print(df)
            print(f"\nData types:")
            print(df.dtypes)
        except Exception as e:
            print(f"Error reading {csv_file}: {e}")

if __name__ == "__main__":
    analyze_csv_files()
