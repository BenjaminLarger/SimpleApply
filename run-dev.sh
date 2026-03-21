#!/bin/bash
# run-dev.sh - Start API server and WXT extension dev server

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$REPO_ROOT/.venv"
EXT_PATH="$REPO_ROOT/extension"
TMP_EXT_PATH="/tmp/simpleApply-ext"

echo "🚀 simpleApply Development Server"
echo "=================================="

# Cleanup function
cleanup() {
    echo ""
    echo "🛑 Shutting down..."
    kill $API_PID 2>/dev/null || true
    kill $WXT_PID 2>/dev/null || true
    wait $API_PID 2>/dev/null || true
    wait $WXT_PID 2>/dev/null || true
    echo "✓ Cleanup complete"
    exit 0
}

# Set trap for cleanup on exit
trap cleanup SIGINT SIGTERM EXIT

# Step 1: Start API Server
echo ""
echo "📡 Starting API Server on port 8765..."
if [ ! -d "$VENV_PATH" ]; then
    echo "❌ Virtual environment not found at $VENV_PATH"
    echo "   Run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

source "$VENV_PATH/bin/activate"
cd "$REPO_ROOT"
python src/api_server.py &
API_PID=$!
sleep 2

# Verify API server is running
if ! curl -s http://localhost:8765/api/health > /dev/null 2>&1; then
    echo "❌ API Server failed to start"
    exit 1
fi
echo "✓ API Server running (PID: $API_PID)"

# Step 2: Set up extension in /tmp (for exFAT workaround)
echo ""
echo "📦 Setting up extension dev environment..."
if [ -d "$TMP_EXT_PATH" ]; then
    rm -rf "$TMP_EXT_PATH"
fi
cp -r "$EXT_PATH" "$TMP_EXT_PATH"

# Install dependencies
cd "$TMP_EXT_PATH"
if ! npm install --silent > /dev/null 2>&1; then
    echo "❌ npm install failed"
    exit 1
fi
echo "✓ Extension dependencies installed"

# Step 3: Start WXT Dev Server
echo ""
echo "🎨 Starting WXT Dev Server on port 3000..."
npm run dev > /tmp/wxt-dev.log 2>&1 &
WXT_PID=$!
sleep 5

# Verify WXT dev server is running
if ! curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "❌ WXT Dev Server failed to start"
    echo "   Check: tail -f /tmp/wxt-dev.log"
    exit 1
fi
echo "✓ WXT Dev Server running (PID: $WXT_PID)"

# Step 4: Ready!
echo ""
echo "✨ Setup complete! Ready to load extension into Chrome."
echo ""
echo "📋 Next steps:"
echo "   1. Open chrome://extensions"
echo "   2. Enable 'Developer mode' (top-right toggle)"
echo "   3. Click 'Load unpacked'"
echo "   4. Select: $TMP_EXT_PATH/.output/chrome-mv3/"
echo ""
echo "🔗 Services:"
echo "   - API Server:       http://localhost:8765"
echo "   - WXT Dev Server:   http://localhost:3000"
echo "   - Extension Build:  $TMP_EXT_PATH/.output/chrome-mv3/"
echo ""
echo "📝 Logs:"
echo "   - WXT Dev:   tail -f /tmp/wxt-dev.log"
echo "   - API:       stdout above"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Keep script running
wait
