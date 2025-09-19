#!/usr/bin/env python3
"""
Python Audio Server - Pure Python replacement for SuperCollider
Implements the same OSC API as supercollider_audio_server_minimal.scd
Uses PyAudio for real-time audio playback with crossfading and mixing
"""

import numpy as np
import soundfile as sf
import pyaudio
import threading
import time
from pythonosc import dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
from typing import Dict, Optional, Tuple
from pathlib import Path
import argparse

class AudioBuffer:
    """Represents an audio buffer with playback capabilities"""
    
    def __init__(self, file_path: str, buffer_id: int, name: str = ""):
        self.buffer_id = buffer_id
        self.name = name
        self.file_path = file_path
        self.audio_data = None
        self.sample_rate = 44100
        self.channels = 2
        self.frames = 0
        self.loaded = False
        
        self.load_audio()
    
    def load_audio(self):
        """Load audio file into memory"""
        try:
            self.audio_data, self.sample_rate = sf.read(self.file_path, dtype=np.float32)
            
            # Ensure stereo
            if len(self.audio_data.shape) == 1:
                self.audio_data = np.column_stack((self.audio_data, self.audio_data))
            elif self.audio_data.shape[1] == 1:
                self.audio_data = np.tile(self.audio_data, (1, 2))
            
            self.frames = len(self.audio_data)
            self.channels = self.audio_data.shape[1]
            self.loaded = True
            
            # Calculate memory usage
            memory_mb = (self.frames * self.channels * 4) / (1024 * 1024)
            print(f"✅ Loaded {self.name} ({memory_mb:.1f} MB)")
            
        except Exception as e:
            print(f"❌ Load failed: {self.name} - {e}")
            self.loaded = False

class StemPlayer:
    """Individual stem player with rate, volume, and position control"""
    
    def __init__(self, buffer: AudioBuffer, rate: float = 1.0, volume: float = 0.8, 
                 start_pos: float = 0.0, loop: bool = True):
        self.buffer = buffer
        self.rate = rate
        self.volume = volume
        self.loop = loop
        self.playing = False
        self.position = int(start_pos * buffer.frames) if buffer.loaded else 0
        self.original_position = self.position
        
    def get_audio_chunk(self, chunk_size: int) -> np.ndarray:
        """Get next audio chunk for playback"""
        if not self.buffer.loaded or not self.playing:
            return np.zeros((chunk_size, 2), dtype=np.float32)
        
        output = np.zeros((chunk_size, 2), dtype=np.float32)
        samples_needed = chunk_size
        output_pos = 0
        
        while samples_needed > 0 and self.playing:
            # Calculate how many samples we can read from current position
            available = self.buffer.frames - self.position
            if available <= 0:
                if self.loop:
                    self.position = 0
                    available = self.buffer.frames
                else:
                    break
            
            # Determine how many samples to read
            to_read = min(samples_needed, available)
            if to_read <= 0:
                break
            
            # Read audio data
            end_pos = self.position + to_read
            audio_chunk = self.buffer.audio_data[self.position:end_pos]
            
            # Apply volume
            audio_chunk = audio_chunk * self.volume
            
            # Copy to output buffer
            output[output_pos:output_pos + to_read] = audio_chunk
            
            # Update positions
            self.position = end_pos
            output_pos += to_read
            samples_needed -= to_read
        
        return output

class PythonAudioServer:
    """Main audio server class - Python replacement for SuperCollider"""
    
    def __init__(self, osc_port: int = 57120, audio_device: Optional[int] = None):
        self.osc_port = osc_port
        self.sample_rate = 44100
        self.chunk_size = 256
        self.channels = 2
        
        # Audio state
        self.buffers: Dict[int, AudioBuffer] = {}
        self.active_players: Dict[int, StemPlayer] = {}
        
        # Mixing parameters
        self.deck_a_volume = 1.0
        self.deck_b_volume = 1.0
        self.master_volume = 0.8
        
        # PyAudio setup
        self.pa = pyaudio.PyAudio()
        self.stream = None
        self.running = False
        
        # OSC server
        self.osc_server = None
        
        print("🎛️💾 PYTHON AUDIO SERVER INITIALIZING 💾🎛️")
        self.setup_audio()
        self.setup_osc()
    
    def setup_audio(self):
        """Initialize PyAudio stream"""
        try:
            self.stream = self.pa.open(
                format=pyaudio.paFloat32,
                channels=self.channels,
                rate=self.sample_rate,
                output=True,
                frames_per_buffer=self.chunk_size
            )
            
            print(f"🔊 Audio stream opened: {self.sample_rate}Hz, {self.chunk_size} samples")
            self.running = True
            
            # Start audio processing thread instead of callback
            self.audio_thread = threading.Thread(target=self.audio_loop)
            self.audio_thread.daemon = True
            self.audio_thread.start()
            
        except Exception as e:
            print(f"❌ Failed to open audio stream: {e}")
    
    def audio_loop(self):
        """Audio processing loop (instead of callback)"""
        while self.running:
            try:
                # Mix all active players
                deck_a_mix = np.zeros((self.chunk_size, 2), dtype=np.float32)
                deck_b_mix = np.zeros((self.chunk_size, 2), dtype=np.float32)
                
                for buffer_id, player in list(self.active_players.items()):
                    if player.playing:
                        try:
                            chunk = player.get_audio_chunk(self.chunk_size)
                            
                            # Route to appropriate deck
                            if buffer_id < 1100:
                                deck_a_mix += chunk
                            else:
                                deck_b_mix += chunk
                                
                        except Exception as e:
                            print(f"⚠️  Error in player {buffer_id}: {e}")
                            player.playing = False
                
                # Apply deck volumes and mix
                final_mix = (deck_a_mix * self.deck_a_volume + 
                            deck_b_mix * self.deck_b_volume) * self.master_volume
                
                # Soft limiting to prevent clipping
                final_mix = np.tanh(final_mix * 0.9) * 0.9
                
                # Write to audio stream
                if self.stream and self.stream.is_active():
                    self.stream.write(final_mix.astype(np.float32).tobytes())
                
                # Small sleep to prevent excessive CPU usage
                time.sleep(0.001)
                
            except Exception as e:
                print(f"❌ Audio loop error: {e}")
                time.sleep(0.1)
    
    def setup_osc(self):
        """Setup OSC server with same API as SuperCollider"""
        disp = dispatcher.Dispatcher()
        
        # Load buffer
        disp.map("/load_buffer", self.osc_load_buffer)
        
        # Play stem
        disp.map("/play_stem", self.osc_play_stem)
        
        # Stop stem
        disp.map("/stop_stem", self.osc_stop_stem)
        
        # Volume control
        disp.map("/stem_volume", self.osc_stem_volume)
        
        # Crossfade
        disp.map("/crossfade_levels", self.osc_crossfade_levels)
        
        # Status
        disp.map("/get_status", self.osc_get_status)
        
        # Test tone
        disp.map("/test_tone", self.osc_test_tone)
        
        # Cleanup
        disp.map("/mixer_cleanup", self.osc_mixer_cleanup)
        
        # Start OSC server - try IPv6 first, then IPv4
        self.osc_server = None
        for bind_addr in ["::", "0.0.0.0"]:  # IPv6 first, then IPv4
            try:
                print(f"🔌 Trying OSC server on {bind_addr}:{self.osc_port}")
                self.osc_server = ThreadingOSCUDPServer(
                    (bind_addr, self.osc_port), disp)
                print(f"✅ OSC server created on {bind_addr}:{self.osc_port}")
                break
            except Exception as e:
                print(f"❌ Failed to bind to {bind_addr}: {e}")
        
        if not self.osc_server:
            print("❌ Could not create OSC server on any interface")
    
    def osc_load_buffer(self, address, *args):
        """Load audio buffer - /load_buffer [buffer_id, file_path, stem_name]"""
        print(f"📡 OSC RECEIVED: {address} {args}")
        try:
            buffer_id = int(args[0])
            file_path = str(args[1])
            stem_name = str(args[2])
            
            # Free existing buffer if it exists
            if buffer_id in self.buffers:
                print(f"Freed buffer {buffer_id}")
                del self.buffers[buffer_id]
            
            # Stop any active player for this buffer
            if buffer_id in self.active_players:
                self.active_players[buffer_id].playing = False
                del self.active_players[buffer_id]
            
            # Load new buffer
            self.buffers[buffer_id] = AudioBuffer(file_path, buffer_id, stem_name)
            
        except Exception as e:
            print(f"❌ Error loading buffer: {e}")
    
    def osc_play_stem(self, address, *args):
        """Play stem - /play_stem [buffer_id, rate, volume, loop, start_pos]"""
        try:
            buffer_id = int(args[0])
            rate = float(args[1])
            volume = float(args[2])
            loop = bool(int(args[3])) if len(args) > 3 else True
            start_pos = float(args[4]) if len(args) > 4 else 0.0
            
            if buffer_id not in self.buffers:
                print(f"❌ Buffer {buffer_id} not loaded")
                return
            
            buffer = self.buffers[buffer_id]
            if not buffer.loaded:
                print(f"❌ Buffer {buffer_id} not ready")
                return
            
            # Stop existing player
            if buffer_id in self.active_players:
                self.active_players[buffer_id].playing = False
            
            # Create new player
            player = StemPlayer(buffer, rate, volume, start_pos, loop)
            player.playing = True
            self.active_players[buffer_id] = player
            
            print(f"▶️  Playing buffer {buffer_id}, rate: {rate:.3f}")
            
        except Exception as e:
            print(f"❌ Error playing stem: {e}")
    
    def osc_stop_stem(self, address, *args):
        """Stop stem playback"""
        try:
            buffer_id = int(args[0])
            if buffer_id in self.active_players:
                self.active_players[buffer_id].playing = False
                del self.active_players[buffer_id]
                print(f"⏹️  Stopped {buffer_id}")
        except Exception as e:
            print(f"❌ Error stopping stem: {e}")
    
    def osc_stem_volume(self, address, *args):
        """Set stem volume"""
        try:
            buffer_id = int(args[0])
            volume = float(args[1])
            if buffer_id in self.active_players:
                self.active_players[buffer_id].volume = volume
        except Exception as e:
            print(f"❌ Error setting volume: {e}")
    
    def osc_crossfade_levels(self, address, *args):
        """Set crossfade levels - /crossfade_levels [deck_a_vol, deck_b_vol]"""
        try:
            self.deck_a_volume = float(args[0])
            self.deck_b_volume = float(args[1])
            print(f"🎚️  A:{self.deck_a_volume:.2f} B:{self.deck_b_volume:.2f}")
        except Exception as e:
            print(f"❌ Error setting crossfade: {e}")
    
    def osc_get_status(self, address, *args):
        """Get server status"""
        try:
            print("=== PYTHON AUDIO SERVER ===")
            print(f"Sample Rate: {self.sample_rate} Hz")
            print(f"Buffers loaded: {len(self.buffers)}")
            print(f"Active players: {len([p for p in self.active_players.values() if p.playing])}")
            print(f"Deck A: {self.deck_a_volume:.2f}, Deck B: {self.deck_b_volume:.2f}")
        except Exception as e:
            print(f"❌ Error getting status: {e}")
    
    def osc_test_tone(self, address, *args):
        """Test tone (simplified - just acknowledge)"""
        freq = args[0] if args else 440
        print(f"🎵 Test tone request: {freq} Hz")
    
    def osc_mixer_cleanup(self, address, *args):
        """Clean up all buffers and players"""
        try:
            # Stop all players
            for player in self.active_players.values():
                player.playing = False
            self.active_players.clear()
            
            # Clear buffers
            self.buffers.clear()
            
            print("🧹 Cleaned")
        except Exception as e:
            print(f"❌ Error cleaning up: {e}")
    
    def start(self):
        """Start the audio server"""
        if self.stream and self.osc_server:
            self.stream.start_stream()
            
            # Start OSC server FIRST
            print(f"🔌 Starting OSC server thread...")
            server_thread = threading.Thread(target=self.osc_server.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            
            # Give OSC server time to bind to port
            print(f"⏳ Waiting for OSC server to bind...")
            time.sleep(0.5)
            print(f"✅ OSC server should be ready")
            
            print("🎛️💾 PYTHON AUDIO SERVER READY 💾🎛️")
            print(f"🔊 Audio: {self.sample_rate}Hz, {self.chunk_size} samples")
            print(f"🔌 OSC: localhost:{self.osc_port}")
            print("💡 Same OSC API as SuperCollider server")
            print()
            
            return server_thread
        else:
            print("❌ Failed to initialize audio server")
            return None
    
    def stop(self):
        """Stop the audio server"""
        self.running = False
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        
        if self.osc_server:
            self.osc_server.shutdown()
        
        if self.pa:
            self.pa.terminate()
        
        print("👋 Python Audio Server stopped")

def main():
    parser = argparse.ArgumentParser(description='Python Audio Server - SuperCollider replacement')
    parser.add_argument('--port', type=int, default=57120, help='OSC port (default: 57120)')
    parser.add_argument('--device', type=int, help='Audio device ID')
    
    args = parser.parse_args()
    
    # Create and start server
    server = PythonAudioServer(osc_port=args.port, audio_device=args.device)
    server_thread = server.start()
    
    if server_thread:
        try:
            # Keep running
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")
            server.stop()

if __name__ == "__main__":
    main()