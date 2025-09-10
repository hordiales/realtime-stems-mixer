#!/bin/bash
# Camelot Wheel Automixer Launcher
# Starts both audio_server.py and camelot_automixer.py

echo "🎯🎵 CAMELOT WHEEL AUTOMIXER LAUNCHER 🎵🎯"
echo "============================================="

# Check if required files exist
if [ ! -f "../audio_server.py" ]; then
    echo "❌ audio_server.py not found"
    exit 1
fi

if [ ! -f "camelot_automixer.py" ]; then
    echo "❌ camelot_automixer.py not found"
    exit 1
fi

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
echo "🎛️💾 Starting Python Audio Server..."
cd ..
/Users/hordia/miniconda3/envs/UBA-crowdstream/bin/python audio_server.py &
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

echo "✅ Audio server is running (PID: $AUDIO_SERVER_PID)"

# Start Camelot automixer in foreground
echo "🎯 Starting Camelot Wheel Automixer..."
echo ""
echo "🎵 CAMELOT HARMONIC MIXING SYSTEM READY 🎵"
echo "================================================="
echo "🎛️ Audio Server: Running in background (PID: $AUDIO_SERVER_PID)"
echo "🎯 Camelot Mixer: Interactive harmonic mode"
echo "💡 Use Ctrl+C to stop both processes"
echo "🎼 Harmonic mixing using Camelot Wheel theory"
echo "================================================="
echo ""

/Users/hordia/miniconda3/envs/UBA-crowdstream/bin/python camelot_automixer.py

# If we get here, Camelot mixer exited normally
cleanup
