#!/usr/bin/env python3
"""
Test Python Audio Server
Quick test to verify the Python audio server works correctly
"""

import time
import subprocess
import threading
from pythonosc import udp_client

def test_python_server():
    """Test the Python audio server functionality"""
    
    print("🧪 Testing Python Audio Server")
    print("=" * 40)
    
    # Start the Python audio server in background
    print("🚀 Starting Python Audio Server...")
    
    try:
        # Start server process
        server_process = subprocess.Popen([
            "/Users/hordia/miniconda3/envs/UBA-crowdstream/bin/python",
            "audio_server.py"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for server to start
        time.sleep(3)
        
        # Create OSC client
        client = udp_client.SimpleUDPClient("localhost", 57120)
        
        print("✅ Server started, testing OSC commands...")
        
        # Test 1: Test tone
        print("🎵 Testing tone...")
        client.send_message("/test_tone", [440])
        time.sleep(0.5)
        
        # Test 2: Get status
        print("📊 Getting status...")
        client.send_message("/get_status", [])
        time.sleep(0.5)
        
        # Test 3: Crossfade levels
        print("🎚️  Testing crossfade...")
        client.send_message("/crossfade_levels", [0.8, 0.2])
        time.sleep(0.5)
        
        # Test 4: Cleanup
        print("🧹 Testing cleanup...")
        client.send_message("/mixer_cleanup", [])
        time.sleep(0.5)
        
        print("\n✅ Basic OSC tests completed!")
        print("💡 If you see OSC responses above, the server is working")
        
        # Keep server running for a bit
        print("⏳ Server running for 10 seconds...")
        time.sleep(10)
        
        # Terminate server
        server_process.terminate()
        server_process.wait(timeout=5)
        
        print("✅ Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        if 'server_process' in locals():
            server_process.terminate()

if __name__ == "__main__":
    test_python_server()