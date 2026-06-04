#!/bin/bash
set -e  # Exit on error

# Change to the correct directory
cd /app || { echo "Failed to cd to /app"; exit 1; }

# Check if .venv exists and is valid
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    rm -rf .venv  # Just in case there's a partial directory
    python -m venv --clear .venv
else
    echo "Using existing virtual environment..."
fi

# Activate venv
echo "Activating virtual environment..."
source .venv/bin/activate

# Ensure pip is installed and up to date
python -m ensurepip --upgrade
pip install --upgrade pip

# Install dependencies and run Streamlit
echo "Installing dependencies..."
pip install -r requirements.txt
echo "Starting Streamlit..."
streamlit run app.py --server.port 8501 --server.headless true