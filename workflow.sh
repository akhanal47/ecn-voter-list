#!/bin/bash

## Full Workflow to get -> transform -> create a single file

## check python, if no get
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null
then
    echo "Python is not installed. Installing Python..."
    
    # Detect OS
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get update
        sudo apt-get install -y python3 python3-pip
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        if ! command -v brew &> /dev/null; then
            echo "Homebrew not found. Installing Homebrew first..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        brew install python3
    else
        echo "Unsupported OS. Please install Python manually from https://www.python.org/downloads/"
        exit 1
    fi
    echo "Python installed successfully!"
else
    echo "Python is already installed."
fi

# use python3
PYTHON_CMD=$(command -v python3 || command -v python)

## get cli args
SOURCE_FOLDER=${1:-voter_data}
DEST_FOLDER=${2:-voter_data_enhanced_english}
DEST_FOLDER_SINGLE_FILE=${3:-single_file}
FINAL_FILE=${4:-consolidated_voter_info.csv}

$PYTHON_CMD get_voter_data.py
$PYTHON_CMD transform.py --source "$SOURCE_FOLDER" --dest "$DEST_FOLDER"
$PYTHON_CMD create_single_file.py --source "$DEST_FOLDER" --dest "$DEST_FOLDER_SINGLE_FILE" --output "$FINAL_FILE"