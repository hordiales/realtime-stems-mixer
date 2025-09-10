#!/bin/bash
# Python DJ System Launcher
# Starts both audio_server.py and dj_plan_executor.py

echo "🐍🎧 Starting Python DJ System 🎧🐍"
echo "=================================="

# Check if plan file exists
PLAN_FILE=${1:-remix_energetic_example.json}

if [ ! -f "$PLAN_FILE" ]; then
    echo "❌ Plan file not found: $PLAN_FILE"
    echo "Available plans:"
    ls remix_*.json 2>/dev/null || echo "No remix plans found"
    exit 1
fi

# Check if required files exist
if [ ! -f "../audio_server.py" ]; then
    echo "❌ audio_server.py not found in parent directory"
    exit 1
fi

if [ ! -f "dj_plan_executor.py" ]; then
    echo "❌ dj_plan_executor.py not found"
    exit 1
fi

echo "📄 Using plan: $PLAN_FILE"
echo ""

# Function to cleanup background processes
cleanup() {
    echo ""
    echo "🛑 Shutting down..."
    if [ ! -z "$AUDIO_SERVER_PID" ]; then
        echo "⏹️  Stopping audio server (PID: $AUDIO_SERVER_PID)..."
        kill $AUDIO_SERVER_PID 2>/dev/null
        # Wait a moment for graceful shutdown
        sleep 1
        # Force kill if still running
        if kill -0 $AUDIO_SERVER_PID 2>/dev/null; then
            echo "🔨 Force killing audio server..."
            kill -9 $AUDIO_SERVER_PID 2>/dev/null
        fi
    fi
    echo "👋 Cleanup complete"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Check and kill any existing audio server processes
echo "🧹 Checking for existing audio server processes..."
EXISTING_PIDS=$(ps aux | grep "audio_server.py" | grep -v grep | awk '{print $2}')
if [ ! -z "$EXISTING_PIDS" ]; then
    echo "⚠️  Found existing audio server processes: $EXISTING_PIDS"
    echo "🔨 Killing existing processes..."
    echo "$EXISTING_PIDS" | xargs kill -9 2>/dev/null
    sleep 1
    echo "✅ Cleanup complete"
fi

# Start audio server in background
echo "🚀 Starting Python Audio Server..."
cd ..
python audio_server.py &
AUDIO_SERVER_PID=$!
cd autodj-plan

# Wait for audio server to initialize
echo "⏳ Waiting for audio server to initialize..."
sleep 3

# Check if audio server is still running
if ! kill -0 $AUDIO_SERVER_PID 2>/dev/null; then
    echo "❌ Audio server failed to start"
    exit 1
fi

# Test server connection
echo "🔌 Testing server connection..."
python -c "
from pythonosc import udp_client
try:
    client = udp_client.SimpleUDPClient('localhost', 57120)
    client.send_message('/test_tone', [440])
    print('✅ Server connection OK')
except Exception as e:
    print(f'❌ Server connection failed: {e}')
    exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ Failed to connect to audio server"
    cleanup
fi

echo "✅ Audio server is running (PID: $AUDIO_SERVER_PID)"

# Start DJ plan executor in foreground
echo "🎵 Starting DJ Plan Executor..."
echo ""
echo "🎧 PYTHON DJ SYSTEM READY 🎧"
echo "================================================="
echo "🎛️ Audio Server: Running in background (PID: $AUDIO_SERVER_PID)"
echo "🎵 DJ Executor: Interactive mode"
echo "💡 Use Ctrl+C to stop both processes"
echo "📄 Plan: $PLAN_FILE"
echo "================================================="
echo "Use 'info' to see plan details, 'full' to play complete mix, or 'quit' to exit"
echo ""

python dj_plan_executor.py "$PLAN_FILE" --mode interactive

# If we get here, DJ executor exited normally
cleanup
