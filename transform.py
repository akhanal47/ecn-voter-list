import pandas as pd
import os
from pathlib import Path
import requests
import argparse


parser = argparse.ArgumentParser(description='Process voter data CSV files')
parser.add_argument('--source', type=str, default='voter_data', help='Source folder containing CSV files of the voter data')
parser.add_argument('--dest', type=str, default='voter_data_enhanced_english', help='Destination folder for processed files')
args = parser.parse_args()

# src and dst
source_folder = args.source
dest_folder = args.dest
os.makedirs(dest_folder, exist_ok=True)

# git for translation
gist_url = 'https://gist.githubusercontent.com/akhanal47/4d2b4f1f259552265a22a645a1105bf1/raw/56154b8cbcb4d7450318c82f3bc7c4196e919ed3/muni_to_english.csv'

municipality_translation = {}

try:
    response = requests.get(gist_url)
    response.raise_for_status()
    
    # parse gist; not found just copy as is
    for line in response.text.strip().split('\n'):
        if ',' in line:
            nepali, english = line.split(',', 1)
            municipality_translation[nepali.strip()] = english.strip()
    
    print(f"Loaded {len(municipality_translation)} municipality translations from Gist")
    
except Exception as e:
    print(f"Warning: Could not load from Gist ({e}). Proceeding without translations.")

# get and process
csv_files = list(Path(source_folder).glob('*.csv'))

for csv_file in csv_files:
    print(f"Processing: {csv_file.name}")
    
    filename = csv_file.stem
    parts = filename.split('_')
    
    province = parts[0]
    municipality = f"{parts[1]}_{parts[2]}"
    ward_no = parts[3]
    polling_place = '_'.join(parts[4:]) if len(parts) > 4 else ''
    
    municipality = municipality.replace('_', ' ')
    polling_place = polling_place.replace('_', ' ')
    
    # not in gist, copy as is
    municipality_en = municipality_translation.get(municipality, municipality)
    
    df = pd.read_csv(csv_file)
    
    df.insert(0, 'Province', province)
    df.insert(1, 'Municipality/Village', municipality)
    df.insert(2, 'Municipality/Village_en', municipality_en)
    df.insert(3, 'Ward No.', ward_no)
    df.insert(4, 'Polling Place', polling_place)
    
    df['Voter Name'] = df['मतदाताको नाम']
    df['Age'] = df['उमेर(वर्ष)']
    df['Sex'] = df['लिङ्ग']
    df['Husband/Wife Name'] = df['पति/पत्नीको नाम']
    df['Father/Mother Name'] = df['पिता/माताको नाम']
    
    df['Married'] = df['पति/पत्नीको नाम'].apply(
        lambda x: 'N' if (x == '-' or x == '' or pd.isna(x)) else 'Y'
    )
    
    df['Sex'] = df['लिङ्ग'].apply(
        lambda x: 'M' if x == 'पुरुष' else "F"
    )

    output_path = os.path.join(dest_folder, csv_file.name)
    df.to_csv(output_path, index=False)
    print(f"Saved: {output_path}")

print(f"\nAll files processed. Total: {len(csv_files)}")