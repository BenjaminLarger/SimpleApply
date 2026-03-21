#!/bin/bash

# AI-Powered Job Application System - Streamlit Runner
# This script sets up the environment and runs the Streamlit application

set -e

echo "🚀 AI-Powered Job Application System - Streamlit UI"
echo "=================================================="

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Please create one first:"
    echo "   python -m venv .venv"
    echo "   source .venv/bin/activate"
    echo "   uv pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Check if required packages are installed
echo "📦 Checking dependencies..."
if ! python -c "import streamlit" 2>/dev/null; then
    echo "📥 Installing dependencies..."
    uv pip install -r requirements.txt
    echo "🌐 Installing Playwright browsers..."
    playwright install chromium
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found. Make sure OPENAI_API_KEY is set."
fi

# Create required directories if they don't exist
echo "📁 Creating required output directories..."
mkdir -p ~/Downloads/Applications/CoverLetters
mkdir -p ~/Downloads/Applications/CVs
echo "✅ Output directories ready"

# Function to find an available port
find_available_port() {
    local port=$1
    local max_attempts=100
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if ! ss -tuln 2>/dev/null | grep -q ":$port "; then
            echo $port
            return 0
        fi
        port=$((port + 1))
        attempt=$((attempt + 1))
    done

    echo "8501"  # Fallback to default if unable to find available port
    return 1
}

# Find an available port starting from 8501
AVAILABLE_PORT=$(find_available_port 8501)

# Start API server on port 8765 in background
API_PID_FILE="/tmp/simpleApply_api.pid"
echo "🔌 Starting API server on port 8765..."
python src/api_server.py &
API_PID=$!
echo $API_PID > "$API_PID_FILE"
echo "✅ API server started (PID $API_PID) on port 8765"

# Cleanup: kill API server and Streamlit on exit
STREAMLIT_PID=""
cleanup() {
    [ -n "$STREAMLIT_PID" ] && kill "$STREAMLIT_PID" 2>/dev/null
    if [ -f "$API_PID_FILE" ]; then
        kill "$(cat "$API_PID_FILE")" 2>/dev/null && echo "🛑 API server stopped"
        rm -f "$API_PID_FILE"
    fi
}
trap cleanup EXIT INT TERM

# Run Streamlit app in background so TERM trap fires immediately
echo "🌐 Starting Streamlit application..."
echo "📱 The app will open in your browser at http://localhost:$AVAILABLE_PORT"
echo ""

streamlit run streamlit_app.py --server.address localhost --server.port $AVAILABLE_PORT &
STREAMLIT_PID=$!
wait $STREAMLIT_PID