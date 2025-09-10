#!/usr/bin/env python3
"""
Direct SuperCollider test to debug audio issues
"""

from pythonosc import udp_client
import time

def main():
    print("🧪 Direct SuperCollider Audio Test")
    
    client = udp_client.SimpleUDPClient("localhost", 57120)
    
    # Test 1: Connection test
    print("\n1️⃣ Testing connection...")
    try:
        client.send_message("/test_tone", [440])
        print("✅ Test tone sent - you should hear a beep")
        time.sleep(2)
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return
    
    # Test 2: Server status
    print("\n2️⃣ Checking server status...")
    try:
        client.send_message("/get_status", [])
        print("✅ Status request sent")
        time.sleep(1)
    except Exception as e:
        print(f"❌ Status failed: {e}")
    
    # Test 3: Load a simple buffer
    print("\n3️⃣ Testing buffer loading...")
    try:
        bass_file = "/Volumes/MacMini2-Extra/crowdstream-data/Eurovision/stems/01-08 Shh (Eurovision 2025 - Cyprus)/bass.wav"
        client.send_message("/load_buffer", [2000, bass_file, "Test_Bass"])
        print(f"✅ Buffer load sent: {bass_file}")
        time.sleep(3)  # Wait for load
    except Exception as e:
        print(f"❌ Buffer load failed: {e}")
        return
    
    # Test 4: Play the buffer
    print("\n4️⃣ Testing playback...")
    try:
        # Play buffer: ID, rate, volume, loop, startPos
        client.send_message("/play_stem", [2000, 1.0, 0.8, 1, 0.0])
        print("✅ Play command sent")
        time.sleep(1)
    except Exception as e:
        print(f"❌ Play failed: {e}")
        return
    
    # Test 5: Check crossfade levels
    print("\n5️⃣ Testing crossfade...")
    try:
        client.send_message("/crossfade_levels", [0.8, 0.8])
        print("✅ Crossfade set to 0.8/0.8")
    except Exception as e:
        print(f"❌ Crossfade failed: {e}")
    
    print(f"\n🎧 You should hear bass playing now...")
    print("⏳ Playing for 10 seconds...")
    time.sleep(10)
    
    # Stop
    print("\n6️⃣ Stopping audio...")
    try:
        client.send_message("/stop_stem", [2000])
        client.send_message("/mixer_cleanup", [])
        print("✅ Stopped")
    except Exception as e:
        print(f"❌ Stop failed: {e}")

if __name__ == "__main__":
    main()