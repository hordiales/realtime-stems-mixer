#!/usr/bin/env python3
"""
Kill All OSC Servers and Background Processes
Cleanup script to stop all Eurovision mixing servers
"""

import subprocess
import time
import signal
import os

def kill_process_by_name(process_name):
    """Kill processes by name"""
    try:
        result = subprocess.run(['pgrep', '-f', process_name], 
                              capture_output=True, text=True)
        
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid.strip():
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                        print(f"✅ Killed {process_name} (PID: {pid})")
                    except ProcessLookupError:
                        print(f"⚠️  Process {pid} already dead")
                    except Exception as e:
                        print(f"❌ Error killing {pid}: {e}")
        else:
            print(f"💡 No {process_name} processes found")
            
    except Exception as e:
        print(f"❌ Error searching for {process_name}: {e}")

def kill_by_port(port):
    """Kill processes using specific ports"""
    try:
        result = subprocess.run(['lsof', '-ti', f':{port}'], 
                              capture_output=True, text=True)
        
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid.strip():
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                        print(f"✅ Killed process on port {port} (PID: {pid})")
                    except ProcessLookupError:
                        print(f"⚠️  Process {pid} already dead")
                    except Exception as e:
                        print(f"❌ Error killing {pid}: {e}")
        else:
            print(f"💡 No processes found on port {port}")
            
    except Exception as e:
        print(f"❌ Error checking port {port}: {e}")

def main():
    print("🛑 EUROVISION MIXER CLEANUP SCRIPT 🛑")
    print("=" * 50)
    
    # Kill specific Python scripts
    scripts_to_kill = [
        'realtime_stem_mixer.py',
        'infinite_dj_remix.py', 
        'live_remix_generator.py',
        'stem_controller.py',
        'osc_controller.py',
        'interactive_remix_player.py'
    ]
    
    print("🔍 Killing Python mixer scripts...")
    for script in scripts_to_kill:
        kill_process_by_name(script)
    
    print("\n🔍 Killing processes on OSC ports...")
    # Kill by common OSC ports
    osc_ports = [5005, 5006, 5007, 8000, 9000]
    for port in osc_ports:
        kill_by_port(port)
 
#warning, following code kills every python/vscode    
#    print("\n🔍 Killing any remaining Python processes with 'eurovision' or 'remix'...")
#    kill_process_by_name('eurovision')
#    kill_process_by_name('remix')
#    kill_process_by_name('stem')
    
    # Wait a moment for processes to die
    time.sleep(2)
    
    print("\n🔍 Final cleanup - force kill if needed...")
    try:
        # Force kill any stubborn processes
        subprocess.run(['pkill', '-9', '-f', 'realtime_stem_mixer'], 
                      capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'infinite_dj_remix'], 
                      capture_output=True)
        subprocess.run(['pkill', '-9', '-f', 'live_remix_generator'], 
                      capture_output=True)
    except:
        pass
    
    print("\n✅ Cleanup complete! All Eurovision mixer servers stopped.")
    print("💡 You can now start fresh servers without port conflicts.")

if __name__ == "__main__":
    main()
