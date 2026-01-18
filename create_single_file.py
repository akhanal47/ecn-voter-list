import pandas as pd
import os
from pathlib import Path
import argparse


parser = argparse.ArgumentParser(description='Process voter data CSV files')
parser.add_argument('--source', type=str, default='voter_data_enhanced_english', help='Source folder containing CSV files of the voter data')
parser.add_argument('--dest', type=str, default='single_file', help='Destination folder for combined single file files')
parser.add_argument('--dest_file', type=str, default='consolidated_voter_info.csv', help='File name for the combined file name')
args = parser.parse_args()

# src and dst
source_folder = args.source
dest_folder = args.dest
dest_fileName = args.dest_file
os.makedirs(dest_folder, exist_ok=True)

csv_files = list(Path(source_folder).glob('*.csv'))

print(f"Found {len(csv_files)} CSV files")

df_list = []
print(df_list)

for csv_file in csv_files:
    print(f"Reading: {csv_file.name}")
    df = pd.read_csv(csv_file)
    df_list.append(df)

consolidated_df = pd.concat(df_list, ignore_index=True)

consolidated_file_path = os.path.join(dest_folder, dest_fileName)
consolidated_df.to_csv(consolidated_file_path, index=False, )

print(f"\nConsolidation complete!")
print(f"Total rows: {len(consolidated_df)}")
print(f"Output file: {consolidated_file_path}")