#!/usr/bin/env python3
"""
Real-Time Eurovision Stem Mixer
Live mixing of individual stems with instant BPM/key control via CLI and OSC
"""

import threading
import time
import queue
import random
import json
import numpy as np
import soundfile as sf
import librosa
from pathlib import Path
import pyaudio
from pythonosc import dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from advanced_mixer import AdvancedMusicMixer
from config_loader import ConfigLoader, MixerConfig

@dataclass
class StemPlayer:
    """Individual stem player with real-time controls"""
    name: str
    audio_data: np.ndarray
    sample_rate: int
    original_bpm: float
    current_bpm: float = field(default_factory=lambda: 125.0)
    volume: float = field(default_factory=lambda: 0.8)
    position: int = field(default_factory=lambda: 0)
    playing: bool = field(default_factory=lambda: True)
    loop: bool = field(default_factory=lambda: True)
    
    def get_samples(self, num_samples: int, target_bpm: float, config=None) -> np.ndarray:
        """Get samples with real-time BPM adjustment"""
        if not self.playing or len(self.audio_data) == 0:
            return np.zeros(num_samples, dtype=np.float32)
        
        # Calculate playback rate for BPM change
        playback_rate = target_bpm / self.original_bpm if self.original_bpm > 0 else 1.0
        
        # Adjust sample count based on playback rate
        source_samples_needed = int(num_samples * playback_rate)
        
        # Get samples from current position
        if self.position + source_samples_needed <= len(self.audio_data):
            samples = self.audio_data[self.position:self.position + source_samples_needed]
            self.position += source_samples_needed
        else:
            # Handle end of audio
            if self.loop:
                # Loop back to beginning
                remaining = len(self.audio_data) - self.position
                first_part = self.audio_data[self.position:] if remaining > 0 else np.array([])
                
                # Reset position and get rest
                loops_needed = (source_samples_needed - len(first_part)) // len(self.audio_data) + 1
                second_part = np.tile(self.audio_data, loops_needed)[:source_samples_needed - len(first_part)]
                
                samples = np.concatenate([first_part, second_part]) if len(first_part) > 0 else second_part
                self.position = len(second_part)
            else:
                # Pad with zeros if not looping
                available = len(self.audio_data) - self.position
                if available > 0:
                    samples = self.audio_data[self.position:]
                    samples = np.pad(samples, (0, source_samples_needed - len(samples)))
                    self.position = len(self.audio_data)
                else:
                    samples = np.zeros(source_samples_needed, dtype=np.float32)
        
        # Time-stretch and pitch-shift based on configuration
        if config:
            # Check if time-stretching is enabled
            if config.audio.enable_time_stretching and abs(playback_rate - 1.0) > config.audio.time_stretch_threshold:
                try:
                    if config.performance.high_quality_time_stretch:
                        # High quality time stretching
                        samples = librosa.effects.time_stretch(samples, rate=1.0/playback_rate, hop_length=config.performance.hop_length)
                    else:
                        # Fast time stretching
                        samples = librosa.effects.time_stretch(samples, rate=1.0/playback_rate)
                except:
                    # Fallback: simple resampling for small changes
                    if abs(playback_rate - 1.0) < 0.1:
                        try:
                            samples = librosa.resample(samples, orig_sr=self.sample_rate, 
                                                     target_sr=int(self.sample_rate/playback_rate))
                        except:
                            pass
            
            # Apply pitch shifting if enabled (currently disabled by default)
            if config.audio.enable_pitch_shifting and config.audio.max_pitch_shift_semitones > 0:
                try:
                    # Calculate pitch shift based on key difference (implementation would go here)
                    # For now, this is disabled by default in config
                    pass
                except:
                    pass
        else:
            # Fallback to original behavior if no config
            if abs(playback_rate - 1.0) > 0.02:
                try:
                    samples = librosa.effects.time_stretch(samples, rate=1.0/playback_rate, hop_length=256)
                except:
                    pass
        
        # Ensure exact output length
        if len(samples) != num_samples:
            if len(samples) > num_samples:
                samples = samples[:num_samples]
            else:
                samples = np.pad(samples, (0, num_samples - len(samples)))
        
        # Apply volume
        return samples * self.volume

@dataclass
class RealtimeSettings:
    """Real-time mixer settings"""
    master_bpm: float = 125.0
    master_key: str = "C"
    master_volume: float = 0.8
    crossfade_mix: float = 0.5  # 0.0 = A only, 1.0 = B only
    stem_volumes: Dict[str, float] = field(default_factory=lambda: {
        'bass': 0.8, 'drums': 0.9, 'vocals': 0.8, 'piano': 0.7, 'other': 0.6
    })

class RealtimeStemMixer:
    """Real-time stem mixer with instant controls"""
    
    def __init__(self, stems_dir: str = "stems", osc_port: int = 5005, config_file: str = "mixer_config.json"):
        # Load configuration
        self.config_loader = ConfigLoader(config_file)
        self.config = self.config_loader.load_config()
        
        # Apply configuration
        self.sample_rate = self.config.audio.sample_rate
        self.chunk_size = self.config.audio.chunk_size
        self.stems_dir = Path(stems_dir)
        
        # Audio setup
        self.pyaudio = pyaudio.PyAudio()
        self.audio_stream = None
        
        # Mixer state (initialized with config values)
        self.settings = RealtimeSettings(
            master_bpm=125.0,
            master_key="C",
            master_volume=self.config.audio.master_volume,
            crossfade_mix=0.5,
            stem_volumes=self.config.mixing.stem_volumes.copy()
        )
        self.settings_lock = threading.Lock()
        
        # Stem players - two decks A and B
        self.deck_a_stems: Dict[str, StemPlayer] = {}
        self.deck_b_stems: Dict[str, StemPlayer] = {}
        self.current_deck = 'A'
        
        # Available songs
        self.mixer = AdvancedMusicMixer(stems_dir, "song-structures")
        self.available_songs = list(self.mixer.songs.keys())
        
        # Control
        self.running = False
        self.osc_port = osc_port
        self.setup_osc()
        
        print("🎛️🔥 REAL-TIME EUROVISION STEM MIXER 🔥🎛️")
        print(f"🎵 Songs Available: {len(self.available_songs)}")
        print(f"🎛️  OSC Port: {osc_port}")
        
    def setup_osc(self):
        """Setup OSC message handlers"""
        self.osc_dispatcher = dispatcher.Dispatcher()
        
        # Master controls
        self.osc_dispatcher.map("/bpm", self.handle_bpm_change)
        self.osc_dispatcher.map("/key", self.handle_key_change)
        self.osc_dispatcher.map("/volume", self.handle_master_volume)
        self.osc_dispatcher.map("/crossfade", self.handle_crossfade)
        
        # Deck controls
        self.osc_dispatcher.map("/deck/a/load", self.handle_load_deck_a)
        self.osc_dispatcher.map("/deck/b/load", self.handle_load_deck_b)
        self.osc_dispatcher.map("/deck/switch", self.handle_switch_deck)
        
        # Individual stem loading for each deck
        self.osc_dispatcher.map("/deck/a/bass", self.handle_load_deck_a_stem)
        self.osc_dispatcher.map("/deck/a/drums", self.handle_load_deck_a_stem)
        self.osc_dispatcher.map("/deck/a/vocals", self.handle_load_deck_a_stem)
        self.osc_dispatcher.map("/deck/a/piano", self.handle_load_deck_a_stem)
        self.osc_dispatcher.map("/deck/a/other", self.handle_load_deck_a_stem)
        
        self.osc_dispatcher.map("/deck/b/bass", self.handle_load_deck_b_stem)
        self.osc_dispatcher.map("/deck/b/drums", self.handle_load_deck_b_stem)
        self.osc_dispatcher.map("/deck/b/vocals", self.handle_load_deck_b_stem)
        self.osc_dispatcher.map("/deck/b/piano", self.handle_load_deck_b_stem)
        self.osc_dispatcher.map("/deck/b/other", self.handle_load_deck_b_stem)
        
        # Stem controls
        self.osc_dispatcher.map("/stem/bass", self.handle_stem_volume)
        self.osc_dispatcher.map("/stem/drums", self.handle_stem_volume)
        self.osc_dispatcher.map("/stem/vocals", self.handle_stem_volume)
        self.osc_dispatcher.map("/stem/piano", self.handle_stem_volume)
        self.osc_dispatcher.map("/stem/other", self.handle_stem_volume)
        
        # Quick controls
        self.osc_dispatcher.map("/random", self.handle_random_mix)
        self.osc_dispatcher.map("/status", self.handle_status)
        
    def load_song_stems(self, song_name: str) -> Dict[str, StemPlayer]:
        """Load all stems for a song"""
        if song_name not in self.mixer.songs:
            print(f"❌ Song not found: {song_name}")
            return {}
            
        song = self.mixer.songs[song_name]
        stems = {}
        
        print(f"🎵 Loading stems for: {song.name.split('(')[0].strip()}")
        
        for stem_type, stem_file in song.stem_files.items():
            try:
                # Load audio file with higher quality
                audio_data, sr = librosa.load(stem_file, sr=self.sample_rate, mono=True, dtype=np.float32)
                
                # Create stem player
                stem_player = StemPlayer(
                    name=f"{song.name}_{stem_type}",
                    audio_data=audio_data,
                    sample_rate=sr,
                    original_bpm=song.bpm,
                    volume=self.settings.stem_volumes.get(stem_type, 0.7)
                )
                
                stems[stem_type] = stem_player
                print(f"    ✅ {stem_type}: {len(audio_data)/sr:.1f}s")
                
            except Exception as e:
                print(f"    ❌ {stem_type}: {e}")
                
        return stems
    
    def load_individual_stem(self, song_name: str, stem_type: str) -> Optional[StemPlayer]:
        """Load a single stem from a specific song"""
        if song_name not in self.mixer.songs:
            print(f"❌ Song not found: {song_name}")
            return None
            
        song = self.mixer.songs[song_name]
        
        if stem_type not in song.stem_files:
            print(f"❌ Stem '{stem_type}' not found in {song_name}")
            return None
            
        try:
            # Load audio file
            audio_data, sr = librosa.load(song.stem_files[stem_type], sr=self.sample_rate, mono=True)
            
            # Create stem player
            stem_player = StemPlayer(
                name=f"{song.name}_{stem_type}",
                audio_data=audio_data,
                sample_rate=sr,
                original_bpm=song.bpm,
                volume=self.settings.stem_volumes.get(stem_type, 0.7)
            )
            
            song_short = song.name.split('(')[0].strip()
            print(f"🎵 Loaded {stem_type}: {song_short} ({len(audio_data)/sr:.1f}s)")
            return stem_player
            
        except Exception as e:
            print(f"❌ Error loading {stem_type} from {song_name}: {e}")
            return None
    
    def audio_callback(self, in_data, frame_count, time_info, status):
        """Real-time audio callback"""
        try:
            with self.settings_lock:
                current_bpm = self.settings.master_bpm
                crossfade = self.settings.crossfade_mix
                master_vol = self.settings.master_volume
            
            # Mix stems from both decks
            mixed_audio = np.zeros(frame_count, dtype=np.float32)
            
            # Deck A (crossfade left side)
            deck_a_mix = np.zeros(frame_count, dtype=np.float32)
            for stem_type, stem_player in self.deck_a_stems.items():
                stem_samples = stem_player.get_samples(frame_count, current_bpm, self.config)
                deck_a_mix += stem_samples
            
            # Deck B (crossfade right side)  
            deck_b_mix = np.zeros(frame_count, dtype=np.float32)
            for stem_type, stem_player in self.deck_b_stems.items():
                stem_samples = stem_player.get_samples(frame_count, current_bpm, self.config)
                deck_b_mix += stem_samples
            
            # Apply crossfade (0.0 = A only, 1.0 = B only)
            deck_a_volume = (1.0 - crossfade)
            deck_b_volume = crossfade
            
            mixed_audio = (deck_a_mix * deck_a_volume) + (deck_b_mix * deck_b_volume)
            
            # Apply master volume and normalize
            mixed_audio *= master_vol
            
            # Prevent clipping with soft limiting
            max_amp = np.max(np.abs(mixed_audio))
            if max_amp > 0.9:
                # Soft limiting instead of hard clipping
                mixed_audio = np.tanh(mixed_audio / max_amp) * 0.9
            
            return (mixed_audio.astype(np.float32).tobytes(), pyaudio.paContinue)
            
        except Exception as e:
            print(f"❌ Audio callback error: {e}")
            return (np.zeros(frame_count, dtype=np.float32).tobytes(), pyaudio.paContinue)
    
    # OSC Handlers
    def handle_bpm_change(self, unused_addr, bpm):
        """Handle real-time BPM change"""
        with self.settings_lock:
            old_bpm = self.settings.master_bpm
            self.settings.master_bpm = max(60.0, min(200.0, float(bpm)))
        print(f"🎵 BPM: {old_bpm:.1f} → {self.settings.master_bpm:.1f} (LIVE)")
        
    def handle_key_change(self, unused_addr, key):
        """Handle key change"""
        with self.settings_lock:
            old_key = self.settings.master_key
            self.settings.master_key = str(key).strip()
        print(f"🎼 Key: {old_key} → {self.settings.master_key}")
        
    def handle_master_volume(self, unused_addr, volume):
        """Handle master volume change"""
        with self.settings_lock:
            old_vol = self.settings.master_volume
            self.settings.master_volume = max(0.0, min(1.0, float(volume)))
        print(f"🔊 Volume: {old_vol:.2f} → {self.settings.master_volume:.2f}")
        
    def handle_crossfade(self, unused_addr, mix):
        """Handle crossfade between decks"""
        with self.settings_lock:
            old_mix = self.settings.crossfade_mix
            self.settings.crossfade_mix = max(0.0, min(1.0, float(mix)))
        print(f"🎚️ Crossfade: {old_mix:.2f} → {self.settings.crossfade_mix:.2f}")
        
    def handle_load_deck_a(self, unused_addr, song_index):
        """Load song into deck A"""
        try:
            index = int(song_index)
            if 0 <= index < len(self.available_songs):
                song_name = self.available_songs[index]
                self.deck_a_stems = self.load_song_stems(song_name)
                print(f"🎵 Deck A: {song_name.split('(')[0].strip()}")
        except Exception as e:
            print(f"❌ Load deck A error: {e}")
            
    def handle_load_deck_b(self, unused_addr, song_index):
        """Load song into deck B"""
        try:
            index = int(song_index)
            if 0 <= index < len(self.available_songs):
                song_name = self.available_songs[index]
                self.deck_b_stems = self.load_song_stems(song_name)
                print(f"🎵 Deck B: {song_name.split('(')[0].strip()}")
        except Exception as e:
            print(f"❌ Load deck B error: {e}")
            
    def handle_switch_deck(self, unused_addr):
        """Switch primary deck"""
        self.current_deck = 'B' if self.current_deck == 'A' else 'A'
        print(f"🔄 Switched to Deck {self.current_deck}")
    
    def handle_load_deck_a_stem(self, address, song_index):
        """Load individual stem into deck A"""
        try:
            stem_type = address.split('/')[-1]  # Extract stem type from address
            index = int(song_index)
            
            if 0 <= index < len(self.available_songs):
                song_name = self.available_songs[index]
                stem_player = self.load_individual_stem(song_name, stem_type)
                
                if stem_player:
                    self.deck_a_stems[stem_type] = stem_player
                    song_short = song_name.split('(')[0].strip()
                    print(f"🎵 Deck A {stem_type}: {song_short}")
                    
        except Exception as e:
            print(f"❌ Load deck A {stem_type} error: {e}")
    
    def handle_load_deck_b_stem(self, address, song_index):
        """Load individual stem into deck B"""
        try:
            stem_type = address.split('/')[-1]  # Extract stem type from address
            index = int(song_index)
            
            if 0 <= index < len(self.available_songs):
                song_name = self.available_songs[index]
                stem_player = self.load_individual_stem(song_name, stem_type)
                
                if stem_player:
                    self.deck_b_stems[stem_type] = stem_player
                    song_short = song_name.split('(')[0].strip()
                    print(f"🎵 Deck B {stem_type}: {song_short}")
                    
        except Exception as e:
            print(f"❌ Load deck B {stem_type} error: {e}")
        
    def handle_stem_volume(self, address, volume):
        """Handle individual stem volume"""
        stem_type = address.split('/')[-1]  # Extract stem type from address
        with self.settings_lock:
            old_vol = self.settings.stem_volumes.get(stem_type, 0.7)
            self.settings.stem_volumes[stem_type] = max(0.0, min(1.0, float(volume)))
            
        # Update stem players
        for stem_player in list(self.deck_a_stems.values()) + list(self.deck_b_stems.values()):
            if stem_type in stem_player.name.lower():
                stem_player.volume = self.settings.stem_volumes[stem_type]
                
        print(f"🎚️ {stem_type}: {old_vol:.2f} → {self.settings.stem_volumes[stem_type]:.2f}")
        
    def handle_random_mix(self, unused_addr):
        """Create random mix"""
        # Random BPM
        new_bpm = random.uniform(80, 160)
        self.handle_bpm_change("", new_bpm)
        
        # Random songs
        if len(self.available_songs) >= 2:
            songs = random.sample(self.available_songs, 2)
            self.handle_load_deck_a("", self.available_songs.index(songs[0]))
            self.handle_load_deck_b("", self.available_songs.index(songs[1]))
            
        # Random crossfade
        self.handle_crossfade("", random.random())
        
        print("🎲 Random mix created!")
        
    def handle_status(self, unused_addr):
        """Show current status"""
        with self.settings_lock:
            print(f"\n🎛️  MIXER STATUS:")
            print(f"🎵 BPM: {self.settings.master_bpm:.1f}")
            print(f"🎼 Key: {self.settings.master_key}")
            print(f"🔊 Volume: {self.settings.master_volume:.2f}")
            print(f"🎚️ Crossfade: {self.settings.crossfade_mix:.2f}")
            print(f"🎵 Deck A: {len(self.deck_a_stems)} stems")
            print(f"🎵 Deck B: {len(self.deck_b_stems)} stems")
    
    def start(self):
        """Start the real-time mixer"""
        if self.running:
            print("⚠️  Already running!")
            return
            
        self.running = True
        
        # Start audio stream
        try:
            self.audio_stream = self.pyaudio.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=self.sample_rate,
                output=True,
                frames_per_buffer=self.chunk_size,
                stream_callback=self.audio_callback
            )
            print(f"🔊 Audio stream started ({self.sample_rate} Hz)")
        except Exception as e:
            print(f"❌ Audio stream error: {e}")
            return
            
        # Start OSC server
        try:
            self.osc_server = ThreadingOSCUDPServer(("localhost", self.osc_port), self.osc_dispatcher)
            self.osc_thread = threading.Thread(target=self.osc_server.serve_forever, daemon=True)
            self.osc_thread.start()
            print(f"🎛️  OSC server started on port {self.osc_port}")
        except Exception as e:
            print(f"❌ OSC server error: {e}")
            
        # Load initial songs
        if len(self.available_songs) >= 2:
            self.deck_a_stems = self.load_song_stems(self.available_songs[0])
            self.deck_b_stems = self.load_song_stems(self.available_songs[1])
            
        print("🎉 Real-Time Stem Mixer is LIVE!")
        
    def stop(self):
        """Stop the mixer"""
        print("🛑 Stopping Real-Time Stem Mixer...")
        self.running = False
        
        if hasattr(self, 'osc_server'):
            self.osc_server.shutdown()
            
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
            
        self.pyaudio.terminate()
        print("✅ Real-Time Stem Mixer stopped")

def main():
    """Main function with CLI"""
    print("🎛️🔥 REAL-TIME EUROVISION STEM MIXER 🔥🎛️")
    print("=" * 60)
    
    try:
        mixer = RealtimeStemMixer()
        mixer.start()
        
        print(f"\n🎛️  LIVE CONTROLS:")
        print("OSC Commands (localhost:5005):")
        print("  /bpm [float]         - Change BPM instantly")
        print("  /key [string]        - Change key")  
        print("  /volume [float]      - Master volume (0.0-1.0)")
        print("  /crossfade [float]   - Crossfade A↔B (0.0-1.0)")
        print("  /deck/a/load [int]   - Load song into deck A")
        print("  /deck/b/load [int]   - Load song into deck B")
        print("  /deck/a/bass [int]   - Load bass from song into deck A")
        print("  /deck/a/drums [int]  - Load drums from song into deck A")
        print("  /deck/a/vocals [int] - Load vocals from song into deck A")
        print("  /deck/b/bass [int]   - Load bass from song into deck B")
        print("  /deck/b/drums [int]  - Load drums from song into deck B")
        print("  /deck/b/vocals [int] - Load vocals from song into deck B")
        print("  /stem/bass [float]   - Bass volume")
        print("  /stem/drums [float]  - Drums volume")
        print("  /stem/vocals [float] - Vocals volume")
        print("  /random              - Random mix")
        print("  /status              - Show status")
        
        print(f"\nCLI Commands:")
        print("  bpm [value]   - Set BPM")
        print("  key [key]     - Set key")
        print("  vol [0-1]     - Master volume")
        print("  cross [0-1]   - Crossfade")
        print("  a [0-10]      - Load song to deck A")
        print("  b [0-10]      - Load song to deck B")
        print("  random        - Random mix")
        print("  status        - Show status")
        print("  q, quit       - Exit")
        print("=" * 60)
        
        # CLI control loop
        while True:
            try:
                cmd = input("🎛️  > ").strip().split()
                if not cmd:
                    continue
                    
                if cmd[0] in ['q', 'quit']:
                    break
                elif cmd[0] == 'bpm' and len(cmd) > 1:
                    mixer.handle_bpm_change("", float(cmd[1]))
                elif cmd[0] == 'key' and len(cmd) > 1:
                    mixer.handle_key_change("", cmd[1])
                elif cmd[0] == 'vol' and len(cmd) > 1:
                    mixer.handle_master_volume("", float(cmd[1]))
                elif cmd[0] == 'cross' and len(cmd) > 1:
                    mixer.handle_crossfade("", float(cmd[1]))
                elif cmd[0] == 'a' and len(cmd) > 1:
                    mixer.handle_load_deck_a("", int(cmd[1]))
                elif cmd[0] == 'b' and len(cmd) > 1:
                    mixer.handle_load_deck_b("", int(cmd[1]))
                elif cmd[0] == 'random':
                    mixer.handle_random_mix("")
                elif cmd[0] == 'status':
                    mixer.handle_status("")
                else:
                    print("❌ Unknown command")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Command error: {e}")
                
        mixer.stop()
        
    except Exception as e:
        print(f"❌ Mixer error: {e}")

if __name__ == "__main__":
    main()