@echo off
REM Full Workflow to get -> transform -> create a single file
REM Check if Python is installed

python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Python is not installed. Downloading and installing Python...
    
    REM Download and install Python 
    echo Downloading Python 3.12 installer...
    curl -o python-installer.exe https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe
        
    echo Installing Python...
    python-installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    
    REM Clean up installer
    del python-installer.exe
    
    REM Refresh environment variables
    echo Python installed successfully! Please restart this script.
    pause
    exit /b
) ELSE (
    echo Python is already installed.
)

REM get cli args with defaults
SET SOURCE_FOLDER=%1
IF "%SOURCE_FOLDER%"=="" SET SOURCE_FOLDER=voter_data

SET DEST_FOLDER=%2
IF "%DEST_FOLDER%"=="" SET DEST_FOLDER=voter_data_enhanced_english

SET DEST_FOLDER_SINGLE_FILE=%3
IF "%DEST_FOLDER_SINGLE_FILE%"=="" SET DEST_FOLDER_SINGLE_FILE=single_file

SET FINAL_FILE=%4
IF "%FINAL_FILE%"=="" SET FINAL_FILE=consolidated_voter_info.csv

python get_voter_data.py
python transform.py --source "%SOURCE_FOLDER%" --dest "%DEST_FOLDER%"
python create_single_file.py --source "%DEST_FOLDER%" --dest "%DEST_FOLDER_SINGLE_FILE%" --output "%FINAL_FILE%"