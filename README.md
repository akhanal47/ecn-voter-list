## Scrape Data from the Election Commision Nepal Voter List

> **⚠️ Warning ⚠️** \
> This is for education purpose only, user is self responsile for any misuse


Step 0. Install Python from [here](https://www.python.org/)

Step 1. Install all the dependencies (requirements.txt)
```
pip install requirements.txt
```

Step 2. Run the `get_voter_data.py` file as `python get_voter_data.py` ; Atleast select the Province and District and click download
> **Note**  Will take a long time, may be hours depending what level you want to extract, the window also may seem to freeze but it is working so wait. DO NOT Let Your Machine go on Sleep Mode

Step 3. Want to transform the data? Run `transform.py`

Step 4. Want to create a single file to use with Excel? Run `create_single_file.py`

> P.S: Opening the csv files in Excel might show random characters (this is due to the encoding issue, the csv files use 'utf-8' encoding). Please follow [the guide](https://www.ias.edu/itg/content/how-import-csv-file-uses-utf-8-character-encoding-0) to properly open 'utf-8' encoded files with excel 


#### Single Command from Step 0 to Step 4 (you will still have to select which data you want to get)

On Linux/Unix bases OS (eg; Mac or Linux)-> will ask for password if python is not there:
```bash
bash workflow.sh
```

On Windows:
```
batch workflow.sh
```


## Want to Get Data For All of Nepal?
> **⚠️ Warning ⚠️** \
This will take likely **take DAYS** to complete

Run `get_voter_data_nepal.py`; if any municipality fails it will be added to a `failed.json` file

> **⚠️ Warning ⚠️** \
Based on how many failed on previous run; This might also **take DAYS** to complete

To re-run for failed municipalities from previous run; Run `get_voter_data_nepal.py --failed.json`

> Once complete (to your desired level); to transform and create a single file; use `Step 3` then `Step 4`