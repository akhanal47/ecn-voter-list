import requests
import csv
import os
from bs4 import BeautifulSoup
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing
import json
import pandas as pd
import time
import threading
import argparse

TIMEOUT = 90
MAX_THREADS = 6

parser = argparse.ArgumentParser(description='Input JSON file')
parser.add_argument('--input_json', type=str, default='municipalities.json', help='Input JSON file containing the list of municipalities')
args = parser.parse_args()

INPUT_JSON_FILE = args.input_json

class VoterListDownloader:
    def __init__(self):
        self.municipalities_data = self.load_municipalities()
        self.output_dir = "voter_data"
        Path(self.output_dir).mkdir(exist_ok=True)
        self.cpu_cores = multiprocessing.cpu_count()
        self.download_cancelled = False
        self.failed_records = []
        self.lock = threading.Lock()
        
    def load_municipalities(self):
        try:
            with open(INPUT_JSON_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print("Error: Input JSON (the file with list of municipalites) not found!")
            return []
    
    def log(self, message):
        print(f"{time.strftime('%H:%M:%S')} - {message}")
    
    def add_failed_record(self, task, error_type, error_message):
        with self.lock:
            self.failed_records.append({
                'province_id': task['province_id'],
                'province': task.get('province', ''),
                'district_id': task['district_id'],
                'district': task['district_name'],
                'municipality_id': task['municipality_id'],
                'municipality': task['municipality_name'],
                'municipality_name': task['municipality_name'],
                'ward_id': task['ward_id'],
                'ward_name': task.get('ward_name', ''),
                'reg_center_id': task['reg_center_id'],
                'reg_center_name': task['reg_center_name'],
                'error_type': error_type,
                'error_message': error_message,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            })
    
    def save_failed_records(self):
        if not self.failed_records:
            self.log("No failed records to save")
            return
        
        # Save as JSON
        json_filepath = 'failed.json'
        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(self.failed_records, f, ensure_ascii=False, indent=2)
        
        self.log(f"Saved {len(self.failed_records)} failed records to {json_filepath}")
        
        # Save as CSV
        csv_filepath = 'failed.csv'
        df = pd.DataFrame(self.failed_records)
        df.to_csv(csv_filepath, index=False, encoding='utf-8-sig')
        
        self.log(f"Saved {len(self.failed_records)} failed records to {csv_filepath}")
    
    def fetch_wards(self, vdc_id):
        url = 'https://voterlist.election.gov.np/index_process.php'
        try:
            response = requests.post(url, data={'vdc': vdc_id, 'list_type': 'ward'}, timeout=TIMEOUT)
            data = response.json()
            if data['status'] == '1':
                soup = BeautifulSoup(data['result'], 'html.parser')
                options = soup.find_all('option')
                return [(opt.get('value'), opt.text.strip()) for opt in options if opt.get('value')]
        except Exception as e:
            self.log(f"Error fetching wards for {vdc_id}: {e}")
        return []
    
    def fetch_reg_centers(self, vdc_id, ward_id):
        url = 'https://voterlist.election.gov.np/index_process.php'
        try:
            response = requests.post(url, data={
                'vdc': vdc_id, 
                'ward': ward_id, 
                'list_type': 'reg_centre'
            }, timeout=TIMEOUT)
            data = response.json()
            if data['status'] == '1':
                soup = BeautifulSoup(data['result'], 'html.parser')
                options = soup.find_all('option')
                return [(opt.get('value'), opt.text.strip()) for opt in options if opt.get('value')]
        except Exception as e:
            self.log(f"Error fetching polling centers for {vdc_id}/{ward_id}: {e}")
        return []
    
    def build_all_tasks(self):
        tasks = []
        
        self.log("Building download tasks from municipalities...")
        
        for mun in self.municipalities_data:
            municipality_id = mun['municipality_id']
            municipality_name = mun['municipality_name']
            province_id = mun['province_id']
            province = mun['province']
            district_id = mun['district_id']
            district_name = mun['district']
            
            self.log(f"Processing: {municipality_name}, {district_name}")
            
            wards = self.fetch_wards(municipality_id)
            
            if not wards:
                self.log(f"No wards found for {municipality_name}")
                continue
            
            for ward_id, ward_name in wards:
                reg_centers = self.fetch_reg_centers(municipality_id, ward_id)
                
                if not reg_centers:
                    self.log(f"No polling centers found for {municipality_name}, Ward {ward_id}")
                    continue
                
                for reg_center_id, reg_center_name in reg_centers:
                    tasks.append({
                        'province_id': province_id,
                        'province': province,
                        'district_id': district_id,
                        'district_name': district_name,
                        'municipality_id': municipality_id,
                        'municipality_name': municipality_name,
                        'ward_id': ward_id,
                        'ward_name': ward_name,
                        'reg_center_id': reg_center_id,
                        'reg_center_name': reg_center_name
                    })
        
        return tasks
    
    def download_all(self):
        tasks = self.build_all_tasks()
        
        if not tasks:
            self.log("No tasks to download!")
            return
        
        total = len(tasks)
        completed = 0
        failed = 0
        
        self.log(f"Starting download of {total} voter lists...")
        
        max_workers = min(MAX_THREADS, self.cpu_cores)
        self.log(f"Using {max_workers} parallel threads")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.download_single_task, task): task 
                      for task in tasks}
            
            for future in as_completed(futures):
                task = futures[future]
                try:
                    success = future.result()
                    if success:
                        completed += 1
                    else:
                        failed += 1
                except Exception as e:
                    failed += 1
                    self.log(f"Error: {task['municipality_name']}/{task['ward_id']}/{task['reg_center_name']} - {e}")
                    self.add_failed_record(task, 'exception', str(e))
                
                if (completed + failed) % 10 == 0:
                    self.log(f"Progress: {completed + failed}/{total} ({completed} success, {failed} failed)")
        
        self.log(f"Download complete: {completed} successful, {failed} failed out of {total}")
        
        # Save failed records at the end
        self.save_failed_records()
    
    def download_single_task(self, task):
        try:
            voters_html = self.extract_voters(
                task['province_id'],
                task['district_id'],
                task['municipality_id'],
                task['ward_id'],
                task['reg_center_id']
            )
            
            soup = BeautifulSoup(voters_html, 'html.parser')
            table = soup.find('table', id='tbl_data')
            
            if not table:
                error_msg = "No table found in response"
                self.log(f"{error_msg}: {task['municipality_name']}/{task['ward_id']}/{task['reg_center_name']}")
                self.add_failed_record(task, 'no_table', error_msg)
                return False
            
            voters_record = self.get_table_rows(table)
            
            if not voters_record:
                error_msg = "No voter records found"
                self.log(f"{error_msg}: {task['municipality_name']}/{task['ward_id']}/{task['reg_center_name']}")
                self.add_failed_record(task, 'no_voters', error_msg)
                return False
            
            filename = f"{task['municipality_name']}_{task['ward_id']}_{task['reg_center_name']}"
            filepath = os.path.join(self.output_dir, f"{filename}.csv")
            
            headers = [
                'सि.नं.', 
                'मतदाता नं', 
                'मतदाताको नाम', 
                'उमेर(वर्ष)', 
                'लिङ्ग', 
                'पति/पत्नीको नाम', 
                'पिता/माताको नाम', 
                'मतदाता विवरण'
            ]
            
            df = pd.DataFrame(voters_record, columns=headers)
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            
            return True
            
        except requests.exceptions.Timeout as e:
            error_msg = f"Request timeout: {str(e)}"
            self.log(f"Timeout: {task['municipality_name']}/{task['ward_id']}/{task['reg_center_name']}")
            self.add_failed_record(task, 'timeout', error_msg)
            return False
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error: {str(e)}"
            self.log(f"Request error: {task['municipality_name']}/{task['ward_id']}/{task['reg_center_name']}")
            self.add_failed_record(task, 'request_error', error_msg)
            return False
        except Exception as e:
            error_msg = str(e)
            self.log(f"Error downloading {task['municipality_name']}/{task['ward_id']}/{task['reg_center_name']}: {error_msg}")
            self.add_failed_record(task, 'unknown_error', error_msg)
            return False
    
    def extract_voters(self, state, district, vdc_mun, ward, reg_centre):
        url = 'https://voterlist.election.gov.np/view_ward.php'
        form_data = {
            'state': state,
            'district': district,
            'vdc_mun': vdc_mun,
            'ward': ward,
            'reg_centre': reg_centre
        }
        response = requests.post(url, data=form_data, timeout=TIMEOUT)
        return response.content
    
    def get_table_rows(self, table):
        data_rows = []
        
        tbody = table.find('tbody')
        if not tbody:
            return data_rows
            
        rows = tbody.find_all('tr')
        
        for row in rows:
            cells = row.find_all('td')
            
            if len(cells) >= 8:
                row_data = {
                    'सि.नं.': cells[0].get_text(strip=True),
                    'मतदाता नं': cells[1].get_text(strip=True),
                    'मतदाताको नाम': cells[2].get_text(strip=True),
                    'उमेर(वर्ष)': cells[3].get_text(strip=True),
                    'लिङ्ग': cells[4].get_text(strip=True),
                    'पति/पत्नीको नाम': cells[5].get_text(strip=True),
                    'पिता/माताको नाम': cells[6].get_text(strip=True),
                    'मतदाता विवरण': cells[7].get_text(strip=True)
                }
                data_rows.append(row_data)
        
        return data_rows

if __name__ == "__main__":
    downloader = VoterListDownloader()
    downloader.download_all()