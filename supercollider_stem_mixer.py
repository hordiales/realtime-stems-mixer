#!/usr/bin/env python3
"""
SuperCollider OSC Stem Mixer - Fixed Version
Real-time stem mixing that sends OSC messages to SuperCollider audio server
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
from pythonosc import dispatcher, udp_client
from pythonosc.osc_server import ThreadingOSCUDPServer
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from config_loader import ConfigLoader, MixerConfig

@dataclass
class OSCStemPlayer:
    """OSC-controlled stem player for SuperCollider"""
    name: str
    audio_file_path: str
    sample_rate: int
    original_bpm: float
    current_bpm: float = field(default_factory=lambda: 125.0)
    volume: float = field(default_factory=lambda: 0.8)
    position: int = field(default_factory=lambda: 0)
    playing: bool = field(default_factory=lambda: True)
    loop: bool = field(default_factory=lambda: True)
    supercollider_synth_id: int = field(default_factory=lambda: 1000)
    
    def send_load_message(self, osc_client: udp_client.SimpleUDPClient) -> None:
        """Send load buffer message to SuperCollider"""
        try:
            # Load buffer in SuperCollider
            osc_client.send_message("/load_buffer", [
                self.supercollider_synth_id,  # Buffer ID
                self.audio_file_path,         # File path
                self.name                     # Stem name
            ])
            print(f"🎵 Loaded {self.name} → SC buffer {self.supercollider_synth_id}")
        except Exception as e:
            print(f"❌ Error loading {self.name}: {e}")
    
    def send_play_message(self, osc_client: udp_client.SimpleUDPClient, target_bpm: float) -> None:
        """Send play message with BPM adjustment to SuperCollider"""
        if not self.playing:
            return
            
        try:
            # Calculate playback rate for BPM change
            playback_rate = target_bpm / self.original_bpm if self.original_bpm > 0 else 1.0
            
            # Send play message to SuperCollider
            osc_client.send_message("/play_stem", [
                self.supercollider_synth_id,  # Buffer ID
                playback_rate,                # Playback rate (BPM adjustment)
                self.volume,                  # Volume
                1 if self.loop else 0,       # Loop flag
                self.position / self.sample_rate  # Start position in seconds
            ])
            
        except Exception as e:
            print(f"❌ Error playing {self.name}: {e}")
    
    def send_volume_message(self, osc_client: udp_client.SimpleUDPClient) -> None:
        """Send volume change to SuperCollider"""
        try:
            osc_client.send_message("/stem_volume", [
                self.supercollider_synth_id,
                self.volume
            ])
        except Exception as e:
            print(f"❌ Error setting volume for {self.name}: {e}")
    
    def send_stop_message(self, osc_client: udp_client.SimpleUDPClient) -> None:
        """Send stop message to SuperCollider"""
        try:
            osc_client.send_message("/stop_stem", [self.supercollider_synth_id])
        except Exception as e:
            print(f"❌ Error stopping {self.name}: {e}")

class SuperColliderStemMixer:
    """Real-time stem mixer with SuperCollider OSC integration"""
    
    def __init__(self, stems_dir: str = "stems", 
                 sc_host: str = "localhost", sc_port: int = 57120,
                 osc_port: int = 5005, config_file: str = "mixer_config.json"):
        
        # Load configuration
        self.config_loader = ConfigLoader(config_file)
        self.config = self.config_loader.load_config()
        
        # SuperCollider OSC client
        self.sc_host = sc_host
        self.sc_port = sc_port
        self.sc_client = udp_client.SimpleUDPClient(sc_host, sc_port)
        
        # Audio settings from config
        self.sample_rate = self.config.audio.sample_rate
        self.chunk_size = self.config.audio.chunk_size
        
        # Mixing state
        self.current_bpm = 125.0
        self.current_key = "C"
        self.crossfade_position = 0.0  # 0.0 = full A, 1.0 = full B
        self.master_volume = self.config.audio.master_volume
        
        # Load songs and stems
        self.stems_dir = Path(stems_dir)
        self.available_songs = []
        self.deck_a_stems = {}
        self.deck_b_stems = {}
        self.stem_volumes = self.config.mixing.stem_volumes.copy()
        
        # Next available synth ID for SuperCollider
        self.next_synth_id = 1000
        
        # Load available songs
        self._load_available_songs()
        
        # Initialize with default songs
        if len(self.available_songs) >= 2:
            self._load_song_to_deck('A', 0)
            self._load_song_to_deck('B', 1)
        
        # OSC server for control
        self.osc_port = osc_port
        self.osc_server = None
        self._setup_osc_server()
        
        # Control thread
        self.running = True
        self.control_thread = threading.Thread(target=self._control_loop, daemon=True)
        
        print(f"🎛️🔥 SUPERCOLLIDER EUROVISION STEM MIXER 🔥🎛️")
        print(f"🎵 Songs Available: {len(self.available_songs)}")
        print(f"🎛️  SuperCollider: {sc_host}:{sc_port}")
        print(f"📡 OSC Control: localhost:{osc_port}")
        print("💡 Use CLI commands or send OSC messages to control")
        
    def _load_available_songs(self):
        """Load available songs from stems directory - supports both directory and flat structure"""
        if not self.stems_dir.exists():
            print(f"❌ Stems directory not found: {self.stems_dir}")
            return
            
        # Group stems by song - look in subdirectories first (current structure)
        song_groups = {}
        
        # Search for stems in subdirectories
        for song_dir in self.stems_dir.iterdir():
            if song_dir.is_dir():
                song_stems = {}
                stem_types = ['bass', 'drums', 'vocals', 'piano', 'other']
                
                # Look for each stem type
                for stem_type in stem_types:
                    stem_file = song_dir / f"{stem_type}.wav"
                    if stem_file.exists():
                        song_stems[stem_type] = stem_file
                
                if len(song_stems) >= 2:  # At least 2 stems required
                    song_id = song_dir.name  # Use directory name as song ID
                    song_groups[song_id] = song_stems
                    print(f"📁 Found song directory: {song_id} ({len(song_stems)} stems)")
        
        # Also search for flat structure files (format: 01-01_bass.wav)
        for stem_file in self.stems_dir.glob("*.wav"):
            parts = stem_file.stem.split("_")
            if len(parts) >= 2:
                song_id = parts[0]
                stem_type = parts[1]
                
                if song_id not in song_groups:
                    song_groups[song_id] = {}
                song_groups[song_id][stem_type] = stem_file
        
        # Create song entries with estimated BPM
        for song_id, stems in song_groups.items():
            if len(stems) >= 2:
                # Extract BPM from any stem file
                estimated_bpm = self._estimate_bpm_from_stem(list(stems.values())[0])
                
                # Clean up song name
                display_name = song_id.replace('_', ' ').replace('-', ' ').title()
                
                self.available_songs.append({
                    'id': song_id,
                    'name': display_name,
                    'stems': stems,
                    'bpm': estimated_bpm,
                    'key': 'C'  # Default key
                })
                print(f"🎵 Loaded: {display_name} ({len(stems)} stems, BPM: {estimated_bpm})")
        
        print(f"✅ Total songs loaded: {len(self.available_songs)}")
    
    def _estimate_bpm_from_stem(self, stem_file: Path) -> float:
        """Quick BPM estimation from a stem file"""
        try:
            # Load a short segment for BPM analysis
            y, sr = sf.read(str(stem_file), frames=44100*10)  # Load 10 seconds max
            if len(y.shape) > 1:
                y = y.mean(axis=1)  # Convert to mono
            
            # Use librosa to estimate tempo
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            return float(tempo) if tempo > 60 and tempo < 200 else 120.0
            
        except Exception as e:
            print(f"⚠️  BPM estimation failed for {stem_file.name}: {e}")
            return 120.0  # Default BPM
    
    def _setup_osc_server(self):
        """Setup OSC server for receiving control messages"""
        if not self.config.osc.enable_osc:
            return
            
        disp = dispatcher.Dispatcher()
        
        # BPM control
        disp.map("/bpm", self.handle_bpm_change)
        disp.map("/tempo", self.handle_bpm_change)
        
        # Deck loading
        disp.map("/deck/a/load", lambda unused_addr, song_id: self._load_song_to_deck('A', song_id))
        disp.map("/deck/b/load", lambda unused_addr, song_id: self._load_song_to_deck('B', song_id))
        
        # Individual stem loading
        disp.map("/deck/a/stem", self._handle_deck_stem_load)
        disp.map("/deck/b/stem", self._handle_deck_stem_load)
        
        # Crossfade control
        disp.map("/crossfade", self.handle_crossfade)
        disp.map("/cross", self.handle_crossfade)
        
        # Stem volume controls
        disp.map("/stem/bass", lambda unused_addr, vol: self._set_stem_volume('bass', vol))
        disp.map("/stem/drums", lambda unused_addr, vol: self._set_stem_volume('drums', vol))
        disp.map("/stem/vocals", lambda unused_addr, vol: self._set_stem_volume('vocals', vol))
        disp.map("/stem/piano", lambda unused_addr, vol: self._set_stem_volume('piano', vol))
        disp.map("/stem/other", lambda unused_addr, vol: self._set_stem_volume('other', vol))
        
        # Master controls
        disp.map("/master_volume", self.handle_master_volume)
        disp.map("/key", self.handle_key_change)
        disp.map("/random", lambda unused_addr: self._randomize_mix())
        disp.map("/status", lambda unused_addr: self._show_status())
        
        try:
            self.osc_server = ThreadingOSCUDPServer((self.config.osc.host, self.osc_port), disp)
            osc_thread = threading.Thread(target=self.osc_server.serve_forever, daemon=True)
            osc_thread.start()
            print(f"📡 OSC server started on {self.config.osc.host}:{self.osc_port}")
        except Exception as e:
            print(f"❌ Failed to start OSC server: {e}")
    
    def _load_song_to_deck(self, deck: str, song_index: int):
        """Load all stems from a song to a deck"""
        if not (0 <= song_index < len(self.available_songs)):
            print(f"❌ Invalid song index: {song_index}")
            return
            
        song = self.available_songs[song_index]
        deck_stems = self.deck_a_stems if deck == 'A' else self.deck_b_stems
        
        # Clear existing stems in deck
        for stem_player in deck_stems.values():
            stem_player.send_stop_message(self.sc_client)
        deck_stems.clear()
        
        # Load new stems
        for stem_type, stem_file in song['stems'].items():
            synth_id = self.next_synth_id
            self.next_synth_id += 1
            
            stem_player = OSCStemPlayer(
                name=f"{song['name']}_{stem_type}",
                audio_file_path=str(stem_file.absolute()),
                sample_rate=self.sample_rate,
                original_bpm=song['bpm'],
                current_bpm=self.current_bpm,
                volume=self.stem_volumes.get(stem_type, 0.8),
                supercollider_synth_id=synth_id
            )
            
            # Send load message to SuperCollider
            stem_player.send_load_message(self.sc_client)
            deck_stems[stem_type] = stem_player
        
        print(f"🎵 Loaded deck {deck}: {song['name']} ({len(deck_stems)} stems)")
        
        # Start playing the stems
        self._update_playback()
    
    def _handle_deck_stem_load(self, unused_addr, deck_letter: str, stem_type: str, song_index: int):
        """Load individual stem from specific song to deck"""
        if not (0 <= song_index < len(self.available_songs)):
            print(f"❌ Invalid song index: {song_index}")
            return
            
        deck = deck_letter.upper()
        song = self.available_songs[song_index]
        deck_stems = self.deck_a_stems if deck == 'A' else self.deck_b_stems
        
        if stem_type not in song['stems']:
            print(f"❌ Stem {stem_type} not found in {song['name']}")
            return
        
        # Stop existing stem of this type
        if stem_type in deck_stems:
            deck_stems[stem_type].send_stop_message(self.sc_client)
        
        # Load new stem
        synth_id = self.next_synth_id
        self.next_synth_id += 1
        
        stem_player = OSCStemPlayer(
            name=f"{song['name']}_{stem_type}",
            audio_file_path=str(song['stems'][stem_type].absolute()),
            sample_rate=self.sample_rate,
            original_bmp=song['bpm'],
            current_bpm=self.current_bpm,
            volume=self.stem_volumes.get(stem_type, 0.8),
            supercollider_synth_id=synth_id
        )
        
        stem_player.send_load_message(self.sc_client)
        deck_stems[stem_type] = stem_player
        
        print(f"🎵 Loaded {deck}.{stem_type}: {song['name']}")
        self._update_playback()
    
    def _set_stem_volume(self, stem_type: str, volume: float):
        """Set volume for specific stem type across both decks"""
        volume = max(0.0, min(1.0, volume))
        self.stem_volumes[stem_type] = volume
        
        # Update volumes in both decks
        for deck_stems in [self.deck_a_stems, self.deck_b_stems]:
            if stem_type in deck_stems:
                deck_stems[stem_type].volume = volume
                deck_stems[stem_type].send_volume_message(self.sc_client)
        
        print(f"🎚️  {stem_type.capitalize()} volume: {volume:.2f}")
    
    def _update_playback(self):
        """Update playback parameters for all stems"""
        try:
            # Send crossfade levels to SuperCollider
            deck_a_level = (1.0 - self.crossfade_position) * self.master_volume
            deck_b_level = self.crossfade_position * self.master_volume
            
            self.sc_client.send_message("/crossfade_levels", [deck_a_level, deck_b_level])
            
            # Update BPM for all stems
            for deck_stems in [self.deck_a_stems, self.deck_b_stems]:
                for stem_player in deck_stems.values():
                    stem_player.current_bpm = self.current_bpm
                    stem_player.send_play_message(self.sc_client, self.current_bpm)
                    
        except Exception as e:
            print(f"❌ Error updating playback: {e}")
    
    def _randomize_mix(self):
        """Create a random mix"""
        # Random BPM
        self.current_bpm = random.uniform(90, 160)
        
        # Random crossfade
        self.crossfade_position = random.uniform(0.0, 1.0)
        
        # Random stem volumes
        for stem_type in self.stem_volumes:
            self.stem_volumes[stem_type] = random.uniform(0.3, 1.0)
        
        # Random songs if available
        if len(self.available_songs) >= 2:
            self._load_song_to_deck('A', random.randint(0, len(self.available_songs) - 1))
            self._load_song_to_deck('B', random.randint(0, len(self.available_songs) - 1))
        
        print(f"🎲 Random mix: BPM {self.current_bpm:.0f}, crossfade {self.crossfade_position:.2f}")
        self._update_playback()
    
    def _show_status(self):
        """Display current mixer status"""
        print("\\n🎛️  SUPERCOLLIDER STEM MIXER STATUS")
        print("=" * 50)
        print(f"🎵 BPM: {self.current_bpm:.1f}")
        print(f"🎹 Key: {self.current_key}")
        print(f"🎚️  Crossfade: {self.crossfade_position:.2f} (0=A, 1=B)")
        print(f"🔊 Master Volume: {self.master_volume:.2f}")
        print(f"🎛️  SuperCollider: {self.sc_host}:{self.sc_port}")
        print()
        
        print("🎵 DECK A:")
        if self.deck_a_stems:
            for stem_type, player in self.deck_a_stems.items():
                print(f"  {stem_type}: {player.name} (vol: {player.volume:.2f}, SC: {player.supercollider_synth_id})")
        else:
            print("  (Empty)")
        
        print("\\n🎵 DECK B:")
        if self.deck_b_stems:
            for stem_type, player in self.deck_b_stems.items():
                print(f"  {stem_type}: {player.name} (vol: {player.volume:.2f}, SC: {player.supercollider_synth_id})")
        else:
            print("  (Empty)")
        
        print(f"\\n🎚️  Stem Volumes:")
        for stem_type, volume in self.stem_volumes.items():
            print(f"  {stem_type}: {volume:.2f}")
        print()
    
    # OSC Handler methods
    def handle_bpm_change(self, unused_addr, bpm: float):
        """Handle BPM change via OSC"""
        bpm = max(60, min(200, bpm))
        self.current_bpm = bpm
        print(f"🎵 BPM: {bpm:.1f}")
        self._update_playback()
    
    def handle_crossfade(self, unused_addr, position: float):
        """Handle crossfade change via OSC"""
        position = max(0.0, min(1.0, position))
        self.crossfade_position = position
        print(f"🎚️  Crossfade: {position:.2f}")
        self._update_playback()
    
    def handle_master_volume(self, unused_addr, volume: float):
        """Handle master volume change via OSC"""
        volume = max(0.0, min(1.0, volume))
        self.master_volume = volume
        print(f"🔊 Master Volume: {volume:.2f}")
        self._update_playback()
    
    def handle_key_change(self, unused_addr, key: str):
        """Handle key change via OSC"""
        self.current_key = key
        print(f"🎹 Key: {key}")
        # Note: Key changes would need pitch shifting in SuperCollider
        # Send key change message
        self.sc_client.send_message("/set_key", [key])
    
    def _control_loop(self):
        """Main control loop for CLI interface"""
        print("\\n💡 CONTROL COMMANDS:")
        print("  bpm <value>     - Set BPM (60-200)")
        print("  key <key>       - Set key (C, Dm, F#, etc.)")
        print("  cross <0-1>     - Crossfade (0=A, 1=B)")
        print("  a <song_num>    - Load song to deck A")
        print("  b <song_num>    - Load song to deck B")
        print("  a.<stem> <song> - Load individual stem to deck A")
        print("  b.<stem> <song> - Load individual stem to deck B")
        print("  bass <0-1>      - Bass volume")
        print("  drums <0-1>     - Drums volume")
        print("  vocals <0-1>    - Vocals volume")
        print("  piano <0-1>     - Piano volume")
        print("  other <0-1>     - Other instruments volume")
        print("  random          - Random mix")
        print("  status          - Show status")
        print("  songs           - List available songs")
        print("  quit            - Exit")
        print()
        
        while self.running:
            try:
                cmd = input("🎛️  > ").strip().lower()
                if not cmd:
                    continue
                    
                parts = cmd.split()
                command = parts[0]
                
                if command == "quit":
                    break
                elif command == "bpm" and len(parts) == 2:
                    try:
                        bpm = float(parts[1])
                        self.handle_bpm_change(None, bpm)
                    except ValueError:
                        print("❌ Invalid BPM value")
                        
                elif command == "key" and len(parts) == 2:
                    self.handle_key_change(None, parts[1])
                    
                elif command == "cross" and len(parts) == 2:
                    try:
                        pos = float(parts[1])
                        self.handle_crossfade(None, pos)
                    except ValueError:
                        print("❌ Invalid crossfade value")
                        
                elif command in ["a", "b"] and len(parts) == 2:
                    try:
                        song_id = int(parts[1])
                        self._load_song_to_deck(command.upper(), song_id)
                    except ValueError:
                        print("❌ Invalid song number")
                        
                elif "." in command and len(parts) == 2:
                    # Individual stem loading: a.bass 3
                    try:
                        deck_stem = command.split(".")
                        if len(deck_stem) == 2:
                            deck, stem = deck_stem
                            song_id = int(parts[1])
                            self._handle_deck_stem_load(None, deck.upper(), stem, song_id)
                    except ValueError:
                        print("❌ Invalid stem loading command")
                        
                elif command in self.stem_volumes and len(parts) == 2:
                    try:
                        volume = float(parts[1])
                        self._set_stem_volume(command, volume)
                    except ValueError:
                        print("❌ Invalid volume value")
                        
                elif command == "random":
                    self._randomize_mix()
                    
                elif command == "status":
                    self._show_status()
                    
                elif command == "songs":
                    print(f"\\n🎵 Available Songs ({len(self.available_songs)}):")
                    for i, song in enumerate(self.available_songs):
                        stems_list = list(song['stems'].keys())
                        print(f"  {i}: {song['name']} (BPM: {song['bpm']}, Stems: {', '.join(stems_list)})")
                    print()
                    
                else:
                    print("❌ Unknown command. Type 'quit' to exit or 'status' for current state.")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Error: {e}")
        
        self.stop()
    
    def start(self):
        """Start the mixer"""
        print("🚀 Starting SuperCollider Stem Mixer...")
        
        # Send initialization message to SuperCollider
        try:
            self.sc_client.send_message("/mixer_init", [
                self.sample_rate,
                len(self.available_songs)
            ])
            print("✅ SuperCollider initialization message sent")
        except Exception as e:
            print(f"⚠️  Could not connect to SuperCollider: {e}")
        
        self.control_thread.start()
        
        try:
            self.control_thread.join()
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Stop the mixer"""
        print("\\n🛑 Stopping SuperCollider Stem Mixer...")
        self.running = False
        
        # Stop all stems
        for deck_stems in [self.deck_a_stems, self.deck_b_stems]:
            for stem_player in deck_stems.values():
                stem_player.send_stop_message(self.sc_client)
        
        # Send cleanup message to SuperCollider
        try:
            self.sc_client.send_message("/mixer_cleanup", [])
        except:
            pass
        
        if self.osc_server:
            self.osc_server.shutdown()
        
        print("👋 Goodbye!")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="SuperCollider Eurovision Stem Mixer")
    parser.add_argument("--stems-dir", default="stems", help="Directory containing stem files")
    parser.add_argument("--sc-host", default="localhost", help="SuperCollider host")
    parser.add_argument("--sc-port", type=int, default=57120, help="SuperCollider OSC port")
    parser.add_argument("--osc-port", type=int, default=5005, help="Control OSC port")
    parser.add_argument("--config", default="mixer_config.json", help="Configuration file")
    
    args = parser.parse_args()
    
    mixer = SuperColliderStemMixer(
        stems_dir=args.stems_dir,
        sc_host=args.sc_host,
        sc_port=args.sc_port,
        osc_port=args.osc_port,
        config_file=args.config
    )
    
    mixer.start()

if __name__ == "__main__":
    main()