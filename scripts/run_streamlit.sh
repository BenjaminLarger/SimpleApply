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

# Run Streamlit app
echo "🌐 Starting Streamlit application..."
echo "📱 The app will open in your browser at http://localhost:8501"
echo ""

streamlit run streamlit_app.py --server.address localhost --server.port 8501