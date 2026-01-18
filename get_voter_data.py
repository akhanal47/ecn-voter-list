import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import json
import requests
import csv
import os
from bs4 import BeautifulSoup
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing
import threading
import time
import pandas as pd


TIMEOUT = 90
MAX_THREADS = 6

class VoterListDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("Nepal Voter List Downloader")
        self.root.geometry("700x700")
        
        # load munis
        self.municipalities_data = self.load_municipalities()
        
        self.output_dir = "voter_data"
        Path(self.output_dir).mkdir(exist_ok=True)
        
        # cou cores
        self.cpu_cores = multiprocessing.cpu_count()
        
        # track download
        self.download_cancelled = False
        self.setup_ui()
        
    def load_municipalities(self):
        try:
            with open('municipalities.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            messagebox.showerror("Error", "municipalities.json not found!")
            return []
    
    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # title and stuffs
        title = ttk.Label(main_frame, text="Nepal Voter List Downloader", 
                         font=('Arial', 16, 'bold'))
        title.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # province and districts are required
        ttk.Label(main_frame, text="Province: *", font=('Arial', 12, 'bold')).grid(
            row=1, column=0, sticky=tk.W, pady=5)
        self.province_var = tk.StringVar()
        self.province_combo = ttk.Combobox(main_frame, textvariable=self.province_var, 
                                           state='readonly', width=40)
        self.province_combo.grid(row=1, column=1, pady=5, sticky=(tk.W, tk.E))
        self.province_combo.bind('<<ComboboxSelected>>', self.on_province_change)
        
        # district
        ttk.Label(main_frame, text="District: *", font=('Arial', 12, 'bold')).grid(
            row=2, column=0, sticky=tk.W, pady=5)
        self.district_var = tk.StringVar()
        self.district_combo = ttk.Combobox(main_frame, textvariable=self.district_var, 
                                           state='readonly', width=40)
        self.district_combo.grid(row=2, column=1, pady=5, sticky=(tk.W, tk.E))
        self.district_combo.bind('<<ComboboxSelected>>', self.on_district_change)
        
        # munis (OPTIONAL)
        ttk.Label(main_frame, text="Municipality:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.municipality_var = tk.StringVar()
        self.municipality_combo = ttk.Combobox(main_frame, textvariable=self.municipality_var, 
                                               state='readonly', width=40)
        self.municipality_combo.grid(row=3, column=1, pady=5, sticky=(tk.W, tk.E))
        self.municipality_combo.bind('<<ComboboxSelected>>', self.on_municipality_change)
        
        # ward no (OPTIONAL)
        ttk.Label(main_frame, text="Ward:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.ward_var = tk.StringVar()
        self.ward_combo = ttk.Combobox(main_frame, textvariable=self.ward_var, 
                                       state='readonly', width=40)
        self.ward_combo.grid(row=4, column=1, pady=5, sticky=(tk.W, tk.E))
        self.ward_combo.bind('<<ComboboxSelected>>', self.on_ward_change)
        
        # reg center (OPTIONAL)
        ttk.Label(main_frame, text="Polling Center:").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.reg_center_var = tk.StringVar()
        self.reg_center_combo = ttk.Combobox(main_frame, textvariable=self.reg_center_var, 
                                             state='readonly', width=40)
        self.reg_center_combo.grid(row=5, column=1, pady=5, sticky=(tk.W, tk.E))
        
        # seperator line
        ttk.Separator(main_frame, orient='horizontal').grid(
            row=6, column=0, columnspan=2, pady=15, sticky=(tk.W, tk.E))
        
        # process parallel? 
        parallel_frame = ttk.LabelFrame(main_frame, text="Download Options", padding="10")
        parallel_frame.grid(row=7, column=0, columnspan=2, pady=10, sticky=(tk.W, tk.E))
        
        self.parallel_var = tk.BooleanVar(value=False)
        parallel_check = ttk.Checkbutton(
            parallel_frame, 
            text=f"Enable parallel downloads (Use {min(self.cpu_cores, MAX_THREADS)} threads)",
            variable=self.parallel_var
        )
        parallel_check.grid(row=0, column=0, sticky=tk.W)
        
        ttk.Label(parallel_frame, text=f"System: {self.cpu_cores} cores detected", 
                 foreground="gray").grid(row=1, column=0, sticky=tk.W)
        
        # logs
        log_frame = ttk.LabelFrame(main_frame, text="Download Log", padding="5")
        log_frame.grid(row=15, column=0, columnspan=2, pady=10, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, width=60, 
                                                  state='disabled', wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # status
        self.status_label = ttk.Label(main_frame, text="Ready", foreground="green")
        self.status_label.grid(row=11, column=0, columnspan=2, pady=5)
        
        # btn
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=12, column=0, columnspan=2, pady=20)
        
        self.download_btn = ttk.Button(button_frame, text="Download Voter Lists", 
                                       command=self.start_download)
        self.download_btn.grid(row=0, column=0, padx=5)
        
        self.cancel_btn = ttk.Button(button_frame, text="Cancel", 
                                     command=self.cancel_download, state='disabled')
        self.cancel_btn.grid(row=0, column=1, padx=5)
        
        ttk.Button(button_frame, text="Change Output Folder", 
                  command=self.change_output_dir).grid(row=0, column=2, padx=5)
        
        ttk.Button(button_frame, text="Clear Log", 
                  command=self.clear_log).grid(row=0, column=3, padx=5)
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(10, weight=1)
        
        self.populate_provinces()
    
    def log(self, message):
        def _log():
            self.log_text.config(state='normal')
            self.log_text.insert(tk.END, f"{time.strftime('%H:%M:%S')} - {message}\n")
            self.log_text.see(tk.END)
            self.log_text.config(state='disabled')
        
        self.root.after(0, _log)

            
    def clear_log(self):
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')
    
    def populate_provinces(self):
        provinces = sorted(set(m['province'] for m in self.municipalities_data))
        self.province_combo['values'] = provinces
    
    def on_province_change(self, event):
        province = self.province_var.get()
        province_id = province.split(' - ')[0]
        
        districts = sorted(set(
            m['district'] for m in self.municipalities_data 
            if m['province_id'] == province_id
        ))
        
        self.district_combo['values'] = districts
        self.district_var.set('')
        self.municipality_combo['values'] = []
        self.municipality_var.set('')
        self.ward_combo['values'] = []
        self.ward_var.set('')
        self.reg_center_combo['values'] = []
        self.reg_center_var.set('')
    
    def on_district_change(self, event):
        district = self.district_var.get()
        district_id = district.split(' - ')[0]
        
        municipalities = sorted(set(
            m['municipality'] for m in self.municipalities_data 
            if m['district_id'] == district_id
        ))
        
        self.municipality_combo['values'] = municipalities
        self.municipality_var.set('')
        self.ward_combo['values'] = []
        self.ward_var.set('')
        self.reg_center_combo['values'] = []
        self.reg_center_var.set('')
    
    def on_municipality_change(self, event):
        if not self.municipality_var.get():
            return
            
        self.status_label.config(text="Loading wards...", foreground="red")
        self.root.update()
        
        municipality = self.municipality_var.get()
        municipality_id = municipality.split(' - ')[0]
        
        wards = self.fetch_wards(municipality_id)
        if wards:
            self.ward_combo['values'] = [f"{w[0]} - {w[1]}" for w in wards]
            self.status_label.config(text="Wards loaded", foreground="green")
        else:
            self.status_label.config(text="Failed to load wards", foreground="red")
        
        self.ward_var.set('')
        self.reg_center_combo['values'] = []
        self.reg_center_var.set('')
    
    def on_ward_change(self, event):
        if not self.ward_var.get():
            return
            
        self.status_label.config(text="Loading polling centers...", foreground="red")
        self.root.update()
        
        municipality = self.municipality_var.get()
        municipality_id = municipality.split(' - ')[0]
        ward = self.ward_var.get()
        ward_id = ward.split(' - ')[0]
        
        reg_centers = self.fetch_reg_centers(municipality_id, ward_id)
        if reg_centers:
            self.reg_center_combo['values'] = [f"{r[0]} - {r[1]}" for r in reg_centers]
            self.status_label.config(text="Polling centers loaded", foreground="green")
        else:
            self.status_label.config(text="Failed to load polling centers", foreground="red")
        
        self.reg_center_var.set('')
    
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
            self.log(f"Error fetching wards: {e}")
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
            self.log(f"Error fetching polling centers: {e}")
        return []
    
    def start_download(self):
        # validate input
        if not self.province_var.get() or not self.district_var.get():
            messagebox.showwarning("Warning", "Province and District are required!")
            return
        
        # create tasks for diff threads
        tasks = self.build_download_tasks()
        
        if not tasks:
            messagebox.showwarning("Warning", "No data to download!")
            return
        
        # confirm before bulk download
        if len(tasks) > 10:
            response = messagebox.askyesno(
                "Confirm Download",
                f"This will download {len(tasks)} voter lists.\n"
                f"Parallel mode: {'Enabled' if self.parallel_var.get() else 'Disabled'}\n\n"
                f"This may take a while. Continue?"
            )
            if not response:
                return
        
        # dwn in separate thread
        self.download_cancelled = False
        thread = threading.Thread(target=self.download_all_tasks, args=(tasks,))
        thread.daemon = True
        thread.start()
    
    def build_download_tasks(self):
        tasks = []
        
        province_id = self.province_var.get().split(' - ')[0]
        district_id = self.district_var.get().split(' - ')[0]
        district_name = self.district_var.get().split(' - ')[1]
        
        # Case 1: polling center is given
        if self.reg_center_var.get():
            municipality_id = self.municipality_var.get().split(' - ')[0]
            municipality_name = self.municipality_var.get().split(' - ')[1]
            ward_id = self.ward_var.get().split(' - ')[0]
            reg_center_id = self.reg_center_var.get().split(' - ')[0]
            reg_center_name = self.reg_center_var.get().split(' - ')[1]
            
            tasks.append({
                'province_id': province_id,
                'district_id': district_id,
                'district_name': district_name,
                'municipality_id': municipality_id,
                'municipality_name': municipality_name,
                'ward_id': ward_id,
                'reg_center_id': reg_center_id,
                'reg_center_name': reg_center_name
            })
        
        # Case 2: ward selected (all centers on that ward)
        elif self.ward_var.get():
            municipality_id = self.municipality_var.get().split(' - ')[0]
            municipality_name = self.municipality_var.get().split(' - ')[1]
            ward_id = self.ward_var.get().split(' - ')[0]
            
            reg_centers = self.fetch_reg_centers(municipality_id, ward_id)
            for reg_center_id, reg_center_name in reg_centers:
                tasks.append({
                    'province_id': province_id,
                    'district_id': district_id,
                    'district_name': district_name,
                    'municipality_id': municipality_id,
                    'municipality_name': municipality_name,
                    'ward_id': ward_id,
                    'reg_center_id': reg_center_id,
                    'reg_center_name': reg_center_name
                })
        
        # Case 3: Selected just upto munis
        elif self.municipality_var.get():
            municipality_id = self.municipality_var.get().split(' - ')[0]
            municipality_name = self.municipality_var.get().split(' - ')[1]
            
            wards = self.fetch_wards(municipality_id)
            for ward_id, ward_name in wards:
                reg_centers = self.fetch_reg_centers(municipality_id, ward_id)
                for reg_center_id, reg_center_name in reg_centers:
                    tasks.append({
                        'province_id': province_id,
                        'district_id': district_id,
                        'district_name': district_name,
                        'municipality_id': municipality_id,
                        'municipality_name': municipality_name,
                        'ward_id': ward_id,
                        'reg_center_id': reg_center_id,
                        'reg_center_name': reg_center_name
                    })
        
        # Case 4: Selected upto District only
        else:
            municipalities = [
                m for m in self.municipalities_data 
                if m['district_id'] == district_id
            ]
            
            for mun in municipalities:
                municipality_id = mun['municipality_id']
                municipality_name = mun['municipality_name']
                
                wards = self.fetch_wards(municipality_id)
                for ward_id, ward_name in wards:
                    reg_centers = self.fetch_reg_centers(municipality_id, ward_id)
                    for reg_center_id, reg_center_name in reg_centers:
                        tasks.append({
                            'province_id': province_id,
                            'district_id': district_id,
                            'district_name': district_name,
                            'municipality_id': municipality_id,
                            'municipality_name': municipality_name,
                            'ward_id': ward_id,
                            'reg_center_id': reg_center_id,
                            'reg_center_name': reg_center_name
                        })
        
        return tasks
    
    def download_all_tasks(self, tasks):
        def _disable_btn():
            self.download_btn.config(state='disabled')
            self.cancel_btn.config(state='normal')
        
        self.root.after(0, _disable_btn)
        
        total = len(tasks)
        completed = 0
        failed = 0

        self.log(f"Starting download of {total} voter lists...")
        
        # parallel or serial
        if self.parallel_var.get():
            max_workers = min(MAX_THREADS, self.cpu_cores)
            self.log(f"Using {max_workers} parallel threads")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(self.download_single_task, task): task 
                        for task in tasks}
                
                for future in as_completed(futures):
                    if self.download_cancelled:
                        executor.shutdown(wait=False)
                        self.log("Download cancelled by user")
                        break
                    
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
                    
        else:
            for task in tasks:
                if self.download_cancelled:
                    self.log("Download cancelled by user")
                    break
                
                try:
                    success = self.download_single_task(task)
                    if success:
                        completed += 1
                    else:
                        failed += 1
                except Exception as e:
                    failed += 1
                    self.log(f"Error: {task['municipality_name']}/{task['ward_id']}/{task['reg_center_name']} - {e}")
                        
        # Final status
        def _final_status():
            self.status_label.config(
                text=f" Complete: {completed} downloaded, {failed} failed",
                foreground="green" if failed == 0 else "orange"
            )
            self.download_btn.config(state='normal')
            self.cancel_btn.config(state='disabled')
            
            if completed > 0:
                messagebox.showinfo("Complete", f"Downloaded {completed} voter lists to:\n{self.output_dir}")
        
        self.root.after(0, _final_status)
        self.log(f"Download complete: {completed} successful, {failed} failed")
    
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
                self.log(f"No table found: {task['municipality_name']}/{task['ward_id']}/{task['reg_center_name']}")
                return False
            
            voters_record = self.get_table_rows(table)
            
            if not voters_record:
                self.log(f"No voters: {task['municipality_name']}/{task['ward_id']}/{task['reg_center_name']}")
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
            
            self.log(f"{filename}.csv ({len(voters_record)} voters)")
            return True
            
        except Exception as e:
            self.log(f"Error downloading {task['municipality_name']}/{task['ward_id']}: {str(e)}")
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
    
    def cancel_download(self):
        self.download_cancelled = True
        self.cancel_btn.config(state='disabled')
        self.log("Cancelling download...")
    
    def change_output_dir(self):
        directory = filedialog.askdirectory(initialdir=self.output_dir)
        if directory:
            self.output_dir = directory
            messagebox.showinfo("Success", f"Output folder changed to:\n{directory}")

if __name__ == "__main__":
    root = tk.Tk()
    app = VoterListDownloader(root)
    root.mainloop()