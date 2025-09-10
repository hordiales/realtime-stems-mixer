#!/usr/bin/env python3
"""
Python Audio Mixer Launcher
Starts both audio_server.py and stem_mixer_smart.py in a coordinated way
"""

import subprocess
import sys
import time
import signal
import os
from pathlib import Path

class PythonMixerLauncher:
    """Launch and manage both Python audio server and stem mixer"""
    
    def __init__(self):
        self.audio_server_process = None
        self.mixer_process = None
        self.running = True
        
        # Setup signal handlers for clean shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\n🛑 Received signal {signum}, shutting down...")
        self.running = False
        self.cleanup()
        sys.exit(0)
    
    def cleanup(self):
        """Stop both processes cleanly"""
        print("🧹 Cleaning up processes...")
        
        if self.mixer_process and self.mixer_process.poll() is None:
            print("⏹️  Stopping stem mixer...")
            self.mixer_process.terminate()
            try:
                self.mixer_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("🔨 Force killing stem mixer...")
                self.mixer_process.kill()
        
        if self.audio_server_process and self.audio_server_process.poll() is None:
            print("⏹️  Stopping audio server...")
            self.audio_server_process.terminate()
            try:
                self.audio_server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("🔨 Force killing audio server...")
                self.audio_server_process.kill()
        
        print("👋 Cleanup complete")
    
    def check_files_exist(self):
        """Check that required files exist"""
        current_dir = Path(__file__).parent
        
        audio_server_file = current_dir / "audio_server.py"
        mixer_file = current_dir / "stem_mixer_smart.py"
        
        if not audio_server_file.exists():
            print(f"❌ audio_server.py not found at {audio_server_file}")
            return False
            
        if not mixer_file.exists():
            print(f"❌ stem_mixer_smart.py not found at {mixer_file}")
            return False
        
        return True
    
    def start_audio_server(self):
        """Start the Python audio server"""
        print("🎛️💾 Starting Python Audio Server...")
        
        try:
            self.audio_server_process = subprocess.Popen(
                [sys.executable, "audio_server.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Wait for server to initialize
            print("⏳ Waiting for audio server to initialize...")
            
            # Read output until we see the ready message
            startup_timeout = 30  # seconds
            start_time = time.time()
            
            while time.time() - start_time < startup_timeout:
                if self.audio_server_process.poll() is not None:
                    # Process died
                    output = self.audio_server_process.stdout.read()
                    print(f"❌ Audio server failed to start:\n{output}")
                    return False
                
                # Check for ready message in a non-blocking way
                try:
                    line = self.audio_server_process.stdout.readline()
                    if line:
                        print(f"🎛️ {line.strip()}")
                        if "PYTHON AUDIO SERVER READY" in line:
                            print("✅ Audio server is ready!")
                            return True
                except:
                    pass
                
                time.sleep(0.1)
            
            print("⚠️  Timeout waiting for audio server, continuing anyway...")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start audio server: {e}")
            return False
    
    def start_stem_mixer(self):
        """Start the stem mixer"""
        print("🧠 Starting Smart Stem Mixer...")
        
        try:
            self.mixer_process = subprocess.Popen(
                [sys.executable, "stem_mixer_smart.py"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            print("✅ Stem mixer started!")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start stem mixer: {e}")
            return False
    
    def monitor_processes(self):
        """Monitor both processes and handle their output"""
        print("\n🎵 PYTHON AUDIO MIXER SYSTEM READY 🎵")
        print("=" * 50)
        print("🎛️ Audio Server: Running in background")
        print("🧠 Stem Mixer: Interactive mode")
        print("💡 Use Ctrl+C to stop both processes")
        print("=" * 50)
        print()
        
        try:
            # Monitor mixer output and forward input
            while self.running:
                # Check if processes are still alive
                if self.audio_server_process.poll() is not None:
                    print("❌ Audio server died unexpectedly!")
                    break
                    
                if self.mixer_process.poll() is not None:
                    print("👋 Stem mixer exited")
                    break
                
                # Forward mixer output
                try:
                    line = self.mixer_process.stdout.readline()
                    if line:
                        print(line.rstrip())
                        # Check for mixer prompt
                        if "🎛️🧠 >" in line:
                            # Read user input and forward to mixer
                            try:
                                user_input = input()
                                if user_input.strip().lower() == 'quit':
                                    print("🛑 User requested quit")
                                    break
                                self.mixer_process.stdin.write(user_input + '\n')
                                self.mixer_process.stdin.flush()
                            except EOFError:
                                break
                            except KeyboardInterrupt:
                                break
                except:
                    time.sleep(0.1)
                    
        except KeyboardInterrupt:
            print("\n🛑 Interrupted by user")
        
        self.running = False
    
    def run(self):
        """Main execution flow"""
        print("🚀 PYTHON AUDIO MIXER LAUNCHER 🚀")
        print("=" * 40)
        
        # Check files exist
        if not self.check_files_exist():
            return 1
        
        # Start audio server
        if not self.start_audio_server():
            return 1
        
        # Wait a bit for audio server to settle
        time.sleep(2)
        
        # Start stem mixer
        if not self.start_stem_mixer():
            self.cleanup()
            return 1
        
        # Wait a bit for mixer to initialize
        time.sleep(1)
        
        # Monitor both processes
        try:
            self.monitor_processes()
        finally:
            self.cleanup()
        
        return 0

def main():
    """Entry point"""
    launcher = PythonMixerLauncher()
    return launcher.run()

if __name__ == "__main__":
    exit(main())