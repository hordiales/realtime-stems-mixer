#!/bin/bash

# Start Python DJ System
# Launches the Python audio server and DJ plan executor

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

echo "📄 Using plan: $PLAN_FILE"
echo ""

# Start Python audio server in background
echo "🚀 Starting Python Audio Server..."
cd .. && python python_audio_server.py &
SERVER_PID=$!

# Wait for server to start
echo "⏳ Waiting for server to initialize..."
sleep 3

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
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

echo ""
echo "🎵 Starting DJ Plan Executor..."
echo "Use 'info' to see plan details, 'full' to play complete mix, or 'quit' to exit"
echo ""

# Start DJ plan executor
python dj_plan_executor.py "$PLAN_FILE" --mode interactive

# Cleanup when done
echo ""
echo "🛑 Shutting down Python DJ System..."
kill $SERVER_PID 2>/dev/null
echo "👋 Goodbye!"
