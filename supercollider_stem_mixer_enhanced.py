#!/usr/bin/env python3
"""
Enhanced SuperCollider OSC Stem Mixer
- Individual stems from different songs
- Section-based playback (verse, chorus, intro, etc.)
- Song structure JSON integration
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
from typing import Dict, List, Optional, Tuple
from config_loader import ConfigLoader, MixerConfig

@dataclass 
class SongSection:
    """Represents a section of a song (verse, chorus, etc.)"""
    start: float
    end: float
    label: str
    duration: float = field(init=False)
    
    def __post_init__(self):
        self.duration = self.end - self.start

@dataclass
class SongStructure:
    """Complete song structure with sections and timing"""
    name: str
    bpm: float
    path: str
    beats: List[float]
    downbeats: List[float]
    sections: List[SongSection]
    
    def get_section_by_label(self, label: str) -> Optional[SongSection]:
        """Get first section matching label"""
        for section in self.sections:
            if section.label.lower() == label.lower():
                return section
        return None
    
    def get_all_sections_by_label(self, label: str) -> List[SongSection]:
        """Get all sections matching label"""
        return [s for s in self.sections if s.label.lower() == label.lower()]

@dataclass
class EnhancedOSCStemPlayer:
    """Enhanced OSC stem player with section support"""
    name: str
    song_name: str
    stem_type: str
    audio_file_path: str
    sample_rate: int
    original_bpm: float
    song_structure: Optional[SongStructure] = None
    current_section: Optional[SongSection] = None
    current_bpm: float = field(default_factory=lambda: 125.0)
    volume: float = field(default_factory=lambda: 0.8)
    position: float = field(default_factory=lambda: 0.0)  # Position in seconds
    playing: bool = field(default_factory=lambda: True)
    loop: bool = field(default_factory=lambda: True)
    supercollider_synth_id: int = field(default_factory=lambda: 1000)
    
    def get_playback_info(self) -> Tuple[float, float]:
        """Get start position and duration based on current section"""
        if self.current_section:
            start_pos = self.current_section.start
            duration = self.current_section.duration
        else:
            start_pos = 0.0
            # Estimate duration from file if no section selected
            try:
                info = sf.info(self.audio_file_path)
                duration = info.frames / info.samplerate
            except:
                duration = 180.0  # Default 3 minutes
        return start_pos, duration
    
    def send_load_message(self, osc_client: udp_client.SimpleUDPClient) -> None:
        """Send load buffer message to SuperCollider"""
        try:
            osc_client.send_message("/load_buffer", [
                self.supercollider_synth_id,
                self.audio_file_path,
                f"{self.name}_{self.current_section.label if self.current_section else 'full'}"
            ])
            section_info = f" [{self.current_section.label}]" if self.current_section else ""
            print(f"🎵 Loaded {self.stem_type}{section_info} from {self.song_name} → SC buffer {self.supercollider_synth_id}")
        except Exception as e:
            print(f"❌ Error loading {self.name}: {e}")
    
    def send_play_message(self, osc_client: udp_client.SimpleUDPClient, target_bpm: float) -> None:
        """Send play message with section and BPM info to SuperCollider"""
        if not self.playing:
            return
            
        try:
            playback_rate = target_bpm / self.original_bpm if self.original_bpm > 0 else 1.0
            start_pos, duration = self.get_playback_info()
            
            # Send enhanced play message with section info
            osc_client.send_message("/play_stem_section", [
                self.supercollider_synth_id,
                playback_rate,
                self.volume,
                1 if self.loop else 0,
                start_pos,  # Start position in seconds
                duration    # Section duration
            ])
            
            section_info = f" [{self.current_section.label} {start_pos:.1f}s-{start_pos+duration:.1f}s]" if self.current_section else ""
            print(f"▶️  Playing {self.stem_type}{section_info} (rate: {playback_rate:.2f}, vol: {self.volume:.2f})")
            
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
    
    def set_section(self, section_label: str) -> bool:
        """Set current section for playback"""
        if not self.song_structure:
            print(f"⚠️  No song structure available for {self.song_name}")
            return False
            
        section = self.song_structure.get_section_by_label(section_label)
        if section:
            self.current_section = section
            print(f"🎯 Set {self.stem_type} to {section_label} section ({section.start:.1f}s-{section.end:.1f}s, {section.duration:.1f}s)")
            return True
        else:
            available_sections = list(set(s.label for s in self.song_structure.sections))
            print(f"❌ Section '{section_label}' not found. Available: {', '.join(available_sections)}")
            return False

class EnhancedSuperColliderStemMixer:
    """Enhanced real-time stem mixer with section support"""
    
    def __init__(self, stems_dir: str = "stems", structures_dir: str = "song-structures",
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
        
        # Directories
        self.stems_dir = Path(stems_dir)
        self.structures_dir = Path(structures_dir)
        
        # Mixing state
        self.current_bpm = 125.0
        self.current_key = "C"
        self.crossfade_position = 0.0
        self.master_volume = self.config.audio.master_volume
        
        # Enhanced song data
        self.available_songs = []
        self.song_structures = {}
        self.deck_a_stems = {}
        self.deck_b_stems = {}
        self.stem_volumes = self.config.mixing.stem_volumes.copy()
        
        # Next available synth ID
        self.next_synth_id = 1000
        
        # Load songs and structures
        self._load_song_structures()
        self._load_available_songs()
        
        # Initialize with default songs (full songs, not sections)
        if len(self.available_songs) >= 2:
            self._load_song_to_deck('A', 0)
            self._load_song_to_deck('B', 1)
        
        # OSC server
        self.osc_port = osc_port
        self.osc_server = None
        self._setup_osc_server()
        
        # Control thread
        self.running = True
        self.control_thread = threading.Thread(target=self._control_loop, daemon=True)
        
        print(f"🎛️🔥 ENHANCED SUPERCOLLIDER EUROVISION STEM MIXER 🔥🎛️")
        print(f"🎵 Songs Available: {len(self.available_songs)}")
        print(f"📊 Song Structures: {len(self.song_structures)}")
        print(f"🎛️  SuperCollider: {sc_host}:{sc_port}")
        print(f"📡 OSC Control: localhost:{osc_port}")
        print("💡 Enhanced features: Individual stems + Section playback")
    
    def _load_song_structures(self):
        """Load song structure JSON files"""
        if not self.structures_dir.exists():
            print(f"⚠️  Song structures directory not found: {self.structures_dir}")
            return
            
        for json_file in self.structures_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Parse sections
                sections = []
                for seg in data.get('segments', []):
                    sections.append(SongSection(
                        start=seg['start'],
                        end=seg['end'],
                        label=seg['label']
                    ))
                
                # Create song structure
                structure = SongStructure(
                    name=json_file.stem,
                    bpm=data.get('bpm', 120),
                    path=data.get('path', ''),
                    beats=data.get('beats', []),
                    downbeats=data.get('downbeats', []),
                    sections=sections
                )
                
                self.song_structures[json_file.stem] = structure
                
                # Show available sections
                section_labels = list(set(s.label for s in sections))
                print(f"📊 Loaded structure: {json_file.stem} (BPM: {structure.bpm}, Sections: {', '.join(section_labels)})")
                
            except Exception as e:
                print(f"❌ Error loading structure {json_file.name}: {e}")
        
        print(f"✅ Loaded {len(self.song_structures)} song structures")
    
    def _load_available_songs(self):
        """Load available songs with structure integration"""
        if not self.stems_dir.exists():
            print(f"❌ Stems directory not found: {self.stems_dir}")
            return
            
        song_groups = {}
        
        # Search for stems in subdirectories
        for song_dir in self.stems_dir.iterdir():
            if song_dir.is_dir():
                song_stems = {}
                stem_types = ['bass', 'drums', 'vocals', 'piano', 'other']
                
                for stem_type in stem_types:
                    stem_file = song_dir / f"{stem_type}.wav"
                    if stem_file.exists():
                        song_stems[stem_type] = stem_file
                
                if len(song_stems) >= 2:
                    song_id = song_dir.name
                    song_groups[song_id] = song_stems
        
        # Create song entries with structure integration
        for song_id, stems in song_groups.items():
            if len(stems) >= 2:
                # Find matching structure
                structure = None
                for struct_name, struct in self.song_structures.items():
                    if song_id in struct_name or any(part in struct_name for part in song_id.split()):
                        structure = struct
                        break
                
                estimated_bpm = structure.bpm if structure else self._estimate_bpm_from_stem(list(stems.values())[0])
                display_name = song_id.replace('_', ' ').replace('-', ' ').title()
                
                song_data = {
                    'id': song_id,
                    'name': display_name,
                    'stems': stems,
                    'bpm': estimated_bpm,
                    'key': 'C',
                    'structure': structure
                }
                
                self.available_songs.append(song_data)
                
                structure_info = f" (Structure: ✅)" if structure else " (Structure: ❌)"
                print(f"🎵 Loaded: {display_name} ({len(stems)} stems, BPM: {estimated_bpm}){structure_info}")
        
        print(f"✅ Total songs loaded: {len(self.available_songs)}")
    
    def _estimate_bpm_from_stem(self, stem_file: Path) -> float:
        """Quick BPM estimation from stem file"""
        try:
            y, sr = sf.read(str(stem_file), frames=44100*10)
            if len(y.shape) > 1:
                y = y.mean(axis=1)
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            return float(tempo) if tempo > 60 and tempo < 200 else 120.0
        except Exception as e:
            return 120.0
    
    def _setup_osc_server(self):
        """Setup enhanced OSC server"""
        if not self.config.osc.enable_osc:
            return
            
        disp = dispatcher.Dispatcher()
        
        # Basic controls
        disp.map("/bpm", self.handle_bpm_change)
        disp.map("/crossfade", self.handle_crossfade)
        disp.map("/master_volume", self.handle_master_volume)
        disp.map("/key", self.handle_key_change)
        disp.map("/random", lambda unused_addr: self._randomize_mix())
        disp.map("/status", lambda unused_addr: self._show_status())
        
        # Enhanced deck loading
        disp.map("/deck/a/load", lambda unused_addr, song_id: self._load_song_to_deck('A', song_id))
        disp.map("/deck/b/load", lambda unused_addr, song_id: self._load_song_to_deck('B', song_id))
        
        # Individual stem loading with section support
        disp.map("/deck/a/stem", self._handle_deck_stem_load)
        disp.map("/deck/b/stem", self._handle_deck_stem_load)
        
        # Section control
        disp.map("/deck/a/section", self._handle_deck_section_change)
        disp.map("/deck/b/section", self._handle_deck_section_change)
        
        # Stem volume controls
        disp.map("/stem/bass", lambda unused_addr, vol: self._set_stem_volume('bass', vol))
        disp.map("/stem/drums", lambda unused_addr, vol: self._set_stem_volume('drums', vol))
        disp.map("/stem/vocals", lambda unused_addr, vol: self._set_stem_volume('vocals', vol))
        disp.map("/stem/piano", lambda unused_addr, vol: self._set_stem_volume('piano', vol))
        disp.map("/stem/other", lambda unused_addr, vol: self._set_stem_volume('other', vol))
        
        try:
            self.osc_server = ThreadingOSCUDPServer((self.config.osc.host, self.osc_port), disp)
            osc_thread = threading.Thread(target=self.osc_server.serve_forever, daemon=True)
            osc_thread.start()
            print(f"📡 Enhanced OSC server started on {self.config.osc.host}:{self.osc_port}")
        except Exception as e:
            print(f"❌ Failed to start OSC server: {e}")
    
    def _load_individual_stem(self, deck: str, song_index: int, stem_type: str, section: str = None) -> bool:
        """Load individual stem from specific song with optional section"""
        if not (0 <= song_index < len(self.available_songs)):
            print(f"❌ Invalid song index: {song_index}")
            return False
            
        song = self.available_songs[song_index]
        deck_stems = self.deck_a_stems if deck == 'A' else self.deck_b_stems
        
        if stem_type not in song['stems']:
            available_stems = list(song['stems'].keys())
            print(f"❌ Stem {stem_type} not found in {song['name']}. Available: {', '.join(available_stems)}")
            return False
        
        # Stop existing stem of this type
        if stem_type in deck_stems:
            deck_stems[stem_type].send_stop_message(self.sc_client)
        
        # Create enhanced stem player
        synth_id = self.next_synth_id
        self.next_synth_id += 1
        
        stem_player = EnhancedOSCStemPlayer(
            name=f"{song['name']}_{stem_type}",
            song_name=song['name'],
            stem_type=stem_type,
            audio_file_path=str(song['stems'][stem_type].absolute()),
            sample_rate=self.sample_rate,
            original_bpm=song['bpm'],
            song_structure=song.get('structure'),
            current_bpm=self.current_bpm,
            volume=self.stem_volumes.get(stem_type, 0.8),
            supercollider_synth_id=synth_id
        )
        
        # Set section if specified
        if section and stem_player.song_structure:
            stem_player.set_section(section)
        
        # Load and play
        stem_player.send_load_message(self.sc_client)
        deck_stems[stem_type] = stem_player
        
        section_info = f" [{section}]" if section else ""
        print(f"🎵 Loaded {deck}.{stem_type}{section_info}: {song['name']}")
        
        # Update playback
        self._update_playback()
        return True
    
    def _handle_deck_stem_load(self, unused_addr, deck_letter: str, stem_type: str, song_index: int, section: str = None):
        """Handle individual stem loading via OSC"""
        deck = deck_letter.upper()
        self._load_individual_stem(deck, song_index, stem_type, section)
    
    def _handle_deck_section_change(self, unused_addr, deck_letter: str, stem_type: str, section: str):
        """Handle section change for existing stem"""
        deck = deck_letter.upper()
        deck_stems = self.deck_a_stems if deck == 'A' else self.deck_b_stems
        
        if stem_type in deck_stems:
            stem_player = deck_stems[stem_type]
            if stem_player.set_section(section):
                # Restart playback with new section
                stem_player.send_play_message(self.sc_client, self.current_bpm)
        else:
            print(f"❌ No {stem_type} stem loaded in deck {deck}")
    
    def _load_song_to_deck(self, deck: str, song_index: int):
        """Load complete song to deck (all stems)"""
        if not (0 <= song_index < len(self.available_songs)):
            print(f"❌ Invalid song index: {song_index}")
            return
            
        song = self.available_songs[song_index]
        deck_stems = self.deck_a_stems if deck == 'A' else self.deck_b_stems
        
        # Clear existing stems
        for stem_player in deck_stems.values():
            stem_player.send_stop_message(self.sc_client)
        deck_stems.clear()
        
        # Load all stems from song
        for stem_type in song['stems'].keys():
            self._load_individual_stem(deck, song_index, stem_type)
        
        print(f"🎵 Loaded complete song to deck {deck}: {song['name']} ({len(deck_stems)} stems)")
    
    def _set_stem_volume(self, stem_type: str, volume: float):
        """Set volume for specific stem type"""
        volume = max(0.0, min(1.0, volume))
        self.stem_volumes[stem_type] = volume
        
        for deck_stems in [self.deck_a_stems, self.deck_b_stems]:
            if stem_type in deck_stems:
                deck_stems[stem_type].volume = volume
                deck_stems[stem_type].send_volume_message(self.sc_client)
        
        print(f"🎚️  {stem_type.capitalize()} volume: {volume:.2f}")
    
    def _update_playback(self):
        """Update playback parameters"""
        try:
            deck_a_level = (1.0 - self.crossfade_position) * self.master_volume
            deck_b_level = self.crossfade_position * self.master_volume
            
            self.sc_client.send_message("/crossfade_levels", [deck_a_level, deck_b_level])
            
            for deck_stems in [self.deck_a_stems, self.deck_b_stems]:
                for stem_player in deck_stems.values():
                    stem_player.current_bpm = self.current_bpm
                    stem_player.send_play_message(self.sc_client, self.current_bpm)
                    
        except Exception as e:
            print(f"❌ Error updating playback: {e}")
    
    def _show_status(self):
        """Show enhanced status with section info"""
        print("\\n🎛️  ENHANCED SUPERCOLLIDER STEM MIXER STATUS")
        print("=" * 60)
        print(f"🎵 BPM: {self.current_bpm:.1f}")
        print(f"🎹 Key: {self.current_key}")
        print(f"🎚️  Crossfade: {self.crossfade_position:.2f}")
        print(f"🔊 Master Volume: {self.master_volume:.2f}")
        
        for deck_name, deck_stems in [("A", self.deck_a_stems), ("B", self.deck_b_stems)]:
            print(f"\\n🎵 DECK {deck_name}:")
            if deck_stems:
                for stem_type, player in deck_stems.items():
                    section_info = f" [{player.current_section.label}]" if player.current_section else " [full]"
                    print(f"  {stem_type}: {player.song_name}{section_info} (vol: {player.volume:.2f})")
            else:
                print("  (Empty)")
        
        print(f"\\n📊 Available Structures: {len(self.song_structures)}")
        print()
    
    def _randomize_mix(self):
        """Create random mix with sections"""
        self.current_bpm = random.uniform(90, 160)
        self.crossfade_position = random.uniform(0.0, 1.0)
        
        # Random songs and sections
        if len(self.available_songs) >= 2:
            song_a = random.choice(self.available_songs)
            song_b = random.choice(self.available_songs)
            
            # Load random stems with random sections
            stems_to_load = random.sample(['bass', 'drums', 'vocals', 'piano', 'other'], random.randint(2, 4))
            
            for stem_type in stems_to_load:
                # Random section selection
                section = None
                if song_a.get('structure'):
                    available_sections = list(set(s.label for s in song_a['structure'].sections))
                    section = random.choice(available_sections)
                
                song_idx_a = self.available_songs.index(song_a)
                song_idx_b = self.available_songs.index(song_b)
                
                self._load_individual_stem('A', song_idx_a, stem_type, section)
                self._load_individual_stem('B', song_idx_b, stem_type, section)
        
        print(f"🎲 Random section mix: BPM {self.current_bpm:.0f}")
    
    # OSC Handler methods
    def handle_bpm_change(self, unused_addr, bpm: float):
        bpm = max(60, min(200, bpm))
        self.current_bpm = bpm
        print(f"🎵 BPM: {bpm:.1f}")
        self._update_playback()
    
    def handle_crossfade(self, unused_addr, position: float):
        position = max(0.0, min(1.0, position))
        self.crossfade_position = position
        print(f"🎚️  Crossfade: {position:.2f}")
        self._update_playback()
    
    def handle_master_volume(self, unused_addr, volume: float):
        volume = max(0.0, min(1.0, volume))
        self.master_volume = volume
        print(f"🔊 Master Volume: {volume:.2f}")
        self._update_playback()
    
    def handle_key_change(self, unused_addr, key: str):
        self.current_key = key
        print(f"🎹 Key: {key}")
        self.sc_client.send_message("/set_key", [key])
    
    def _control_loop(self):
        """Enhanced control loop with section commands"""
        print("\\n💡 ENHANCED CONTROL COMMANDS:")
        print("=== BASIC CONTROLS ===")
        print("  bpm <value>           - Set BPM (60-200)")
        print("  key <key>             - Set key") 
        print("  cross <0-1>           - Crossfade")
        print("  songs                 - List songs")
        print("  status                - Show status")
        print("  quit                  - Exit")
        print()
        print("=== FULL SONG LOADING ===")
        print("  a <song_num>          - Load complete song to deck A")
        print("  b <song_num>          - Load complete song to deck B")
        print()
        print("=== INDIVIDUAL STEM LOADING ===")
        print("  a.<stem> <song_num>   - Load stem to deck A")
        print("  b.<stem> <song_num>   - Load stem to deck B")
        print("  Examples: a.bass 3, b.drums 7")
        print()
        print("=== SECTION CONTROL ===")
        print("  a.<stem>.<section> <song_num> - Load stem with specific section")
        print("  b.<stem>.<section> <song_num> - Load stem with specific section")
        print("  section a <stem> <section>    - Change section for existing stem")
        print("  Examples: a.bass.chorus 2, section a vocals verse")
        print()
        print("=== VOLUME CONTROLS ===")
        print("  bass/drums/vocals/piano/other <0-1> - Set stem volume")
        print()
        print("=== SPECIAL ===")
        print("  random                - Random section mix")
        print("  sections <song_num>   - Show available sections for song")
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
                    # Enhanced stem loading with section support
                    try:
                        deck_parts = command.split(".")
                        song_id = int(parts[1])
                        
                        if len(deck_parts) == 2:
                            # Format: a.bass 3
                            deck, stem = deck_parts
                            self._load_individual_stem(deck.upper(), song_id, stem)
                        elif len(deck_parts) == 3:
                            # Format: a.bass.chorus 3  
                            deck, stem, section = deck_parts
                            self._load_individual_stem(deck.upper(), song_id, stem, section)
                    except ValueError:
                        print("❌ Invalid stem loading command")
                        
                elif command == "section" and len(parts) == 4:
                    # Format: section a bass chorus
                    try:
                        deck = parts[1].upper()
                        stem_type = parts[2]
                        section = parts[3]
                        self._handle_deck_section_change(None, deck, stem_type, section)
                    except:
                        print("❌ Invalid section command")
                        
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
                        structure_info = "📊" if song.get('structure') else "❌"
                        print(f"  {i}: {song['name']} (BPM: {song['bpm']:.0f}, Stems: {len(stems_list)}, Structure: {structure_info})")
                    print()
                
                elif command == "sections" and len(parts) == 2:
                    try:
                        song_idx = int(parts[1])
                        if 0 <= song_idx < len(self.available_songs):
                            song = self.available_songs[song_idx]
                            if song.get('structure'):
                                sections = song['structure'].sections
                                print(f"\\n📊 Sections for {song['name']}:")
                                for section in sections:
                                    print(f"  {section.label}: {section.start:.1f}s - {section.end:.1f}s ({section.duration:.1f}s)")
                                print()
                            else:
                                print(f"❌ No structure data for {song['name']}")
                        else:
                            print("❌ Invalid song number")
                    except ValueError:
                        print("❌ Invalid song number")
                        
                else:
                    print("❌ Unknown command. Type 'quit' to exit or see commands above.")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Error: {e}")
        
        self.stop()
    
    def start(self):
        """Start the enhanced mixer"""
        print("🚀 Starting Enhanced SuperCollider Stem Mixer...")
        
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
        print("\\n🛑 Stopping Enhanced SuperCollider Stem Mixer...")
        self.running = False
        
        for deck_stems in [self.deck_a_stems, self.deck_b_stems]:
            for stem_player in deck_stems.values():
                stem_player.send_stop_message(self.sc_client)
        
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
    
    parser = argparse.ArgumentParser(description="Enhanced SuperCollider Eurovision Stem Mixer")
    parser.add_argument("--stems-dir", default="stems", help="Directory containing stem files")
    parser.add_argument("--structures-dir", default="song-structures", help="Directory containing song structure JSON files")
    parser.add_argument("--sc-host", default="localhost", help="SuperCollider host")
    parser.add_argument("--sc-port", type=int, default=57120, help="SuperCollider OSC port")
    parser.add_argument("--osc-port", type=int, default=5005, help="Control OSC port")
    parser.add_argument("--config", default="mixer_config.json", help="Configuration file")
    
    args = parser.parse_args()
    
    mixer = EnhancedSuperColliderStemMixer(
        stems_dir=args.stems_dir,
        structures_dir=args.structures_dir,
        sc_host=args.sc_host,
        sc_port=args.sc_port,
        osc_port=args.osc_port,
        config_file=args.config
    )
    
    mixer.start()

if __name__ == "__main__":
    main()