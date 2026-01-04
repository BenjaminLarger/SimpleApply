#!/bin/bash

# Kill existing Streamlit process
pkill -f "streamlit run" || true

# Wait a moment for the process to fully terminate
sleep 1

# Get the project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate virtual environment if it exists
if [ -f "$PROJECT_DIR/.venv/bin/activate" ]; then
    source "$PROJECT_DIR/.venv/bin/activate"
fi

# Run the Streamlit app in the background
cd "$PROJECT_DIR"
streamlit run streamlit_app.py > /tmp/streamlit-app.log 2>&1 &

echo "Streamlit app restarted in background (PID: $!)"
