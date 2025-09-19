#!/usr/bin/env python3
"""
Smart Loading SuperCollider Stem Mixer
- Only loads stems when actually playing them
- Perfect for 16GB systems
"""

import threading
import time
import random
import json
import math
from pathlib import Path
from pythonosc import dispatcher, udp_client
from pythonosc.osc_server import ThreadingOSCUDPServer
from typing import Dict, List, Optional
from config_loader import ConfigLoader, MixerConfig

class SmartSuperColliderStemMixer:
    """Smart loading stem mixer - only loads what's playing"""
    
    def __init__(self, stems_dir: str = "stems", structures_dir: str = "song-structures",
                 sc_host: str = "localhost", sc_port: int = 57120,
                 osc_port: int = 5005, config_file: str = "mixer_config.json"):
        
        # Load configuration
        self.config_loader = ConfigLoader(config_file)
        self.config = self.config_loader.load_config()
        
        # SuperCollider OSC client
        self.sc_host = sc_host
        self.sc_port = sc_port
        # Force IPv4 to match audio server
        sc_host_ipv4 = "127.0.0.1" if sc_host == "localhost" else sc_host
        self.sc_client = udp_client.SimpleUDPClient(sc_host_ipv4, sc_port)
        
        # Directories
        self.stems_dir = Path(stems_dir)
        self.structures_dir = Path(structures_dir)
        
        # Mixing state
        self.current_bpm = 125.0
        self.current_key = "C"
        self.crossfade_position = 0.0
        self.master_volume = self.config.audio.master_volume
        
        # Temporal synchronization
        self.sync_enabled = True           # Enable/disable temporal sync
        self.beat_duration = 60.0 / self.current_bpm  # Seconds per beat
        self.master_start_time = time.time()  # Global timeline reference
        self.quantize_resolution = 4       # Quantize to quarter notes (1=whole, 2=half, 4=quarter)
        self.pending_stems = []            # Stems waiting for next quantized beat
        
        # Smart loading state
        self.available_songs = []
        self.song_structures = {}
        self.loaded_buffers = set()        # Track what's loaded in SuperCollider
        self.playing_stems = set()         # Track what's currently playing
        self.deck_a_stems = {}             # Current deck A configuration
        self.deck_b_stems = {}             # Current deck B configuration
        self.stem_volumes = self.config.mixing.stem_volumes.copy()
        
        # Buffer ID management
        self.next_synth_id = 1000
        
        # Load song information
        self._load_song_info()
        
        # OSC server
        self.osc_port = osc_port
        self.osc_server = None
        self._setup_osc_server()
        
        # Control thread
        self.running = True
        self.control_thread = threading.Thread(target=self._control_loop, daemon=True)
        
        print(f"🎛️🧠 SMART LOADING EUROVISION STEM MIXER 🧠🎛️")
        print(f"🎵 Songs Available: {len(self.available_songs)}")
        print(f"📊 Song Structures: {len(self.song_structures)}")
        print(f"🎛️  SuperCollider: {sc_host}:{sc_port}")
        print(f"📡 OSC Control: localhost:{osc_port}")
        print("💡 Smart Loading: Only loads stems when playing")
        
    def _extract_country_name(self, song_name: str) -> str:
        """Extract country name from Eurovision song title"""
        # Common Eurovision patterns: "01-01 Title (Eurovision 2025 - Country)"
        if '(' in song_name and ')' in song_name:
            paren_content = song_name.split('(')[-1].split(')')[0]
            if '-' in paren_content:
                country = paren_content.split('-')[-1].strip()
                return country.lower()
        
        # Fallback patterns
        for delimiter in ['-', '(', ')']:
            if delimiter in song_name:
                parts = song_name.replace('(', ' ').replace(')', ' ').replace('-', ' ').split()
                # Look for country names in common positions
                for part in reversed(parts):  # Check from end first
                    clean_part = part.strip().lower()
                    if len(clean_part) > 3 and clean_part.isalpha():
                        return clean_part
        
        return song_name.lower()
    
    def _find_song_by_identifier(self, identifier: str) -> Optional[int]:
        """Find song by country name or numerical ID"""
        # Try numerical ID first
        try:
            song_id = int(identifier)
            if 0 <= song_id < len(self.available_songs):
                return song_id
        except ValueError:
            pass
        
        # Try country name matching
        identifier_lower = identifier.lower().strip()
        
        # First pass: exact country name match
        for i, song in enumerate(self.available_songs):
            country = self._extract_country_name(song['name'])
            if country == identifier_lower:
                return i
        
        # Second pass: partial country name match
        for i, song in enumerate(self.available_songs):
            country = self._extract_country_name(song['name'])
            if identifier_lower in country or country.startswith(identifier_lower):
                return i
        
        # Third pass: check if identifier appears anywhere in song name
        for i, song in enumerate(self.available_songs):
            if identifier_lower in song['name'].lower():
                return i
        
        return None
    
    def _load_song_info(self):
        """Load song and structure information (metadata only)"""
        # Load structure JSON files
        if self.structures_dir.exists():
            for json_file in self.structures_dir.glob("*.json"):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    sections = []
                    for seg in data.get('segments', []):
                        sections.append({
                            'start': seg['start'],
                            'end': seg['end'], 
                            'label': seg['label']
                        })
                    
                    self.song_structures[json_file.stem] = {
                        'bpm': data.get('bpm', 120),
                        'sections': sections
                    }
                except Exception as e:
                    print(f"⚠️  Could not load structure {json_file.name}: {e}")
        
        # Load song directory info (no audio loading yet)
        if self.stems_dir.exists():
            for song_dir in self.stems_dir.iterdir():
                if song_dir.is_dir():
                    song_stems = {}
                    stem_types = ['bass', 'drums', 'vocals', 'piano', 'other']
                    
                    for stem_type in stem_types:
                        stem_file = song_dir / f"{stem_type}.wav"
                        if stem_file.exists():
                            song_stems[stem_type] = stem_file
                    
                    if len(song_stems) >= 2:
                        # Find matching structure
                        structure = None
                        for struct_name, struct_data in self.song_structures.items():
                            if song_dir.name in struct_name:
                                structure = struct_data
                                break
                        
                        bpm = structure['bpm'] if structure else 120.0
                        sections = structure['sections'] if structure else []
                        
                        # Extract country name for easy identification
                        country_name = self._extract_country_name(song_dir.name)
                        
                        song_data = {
                            'id': song_dir.name,
                            'name': song_dir.name.replace('_', ' ').title(),
                            'country': country_name,
                            'stems': song_stems,
                            'bpm': bpm,
                            'sections': sections
                        }
                        
                        self.available_songs.append(song_data)
                        
                        section_labels = list(set(s['label'] for s in sections)) if sections else []
                        structure_status = "✅" if structure else "❌"
                        print(f"📋 Found: {song_data['name']} | Country: {country_name.title()} | BPM: {bpm} | Structure: {structure_status} | Sections: {len(section_labels)}")
        
        print(f"✅ Total songs indexed: {len(self.available_songs)}")
    
    def _get_current_beat_position(self) -> float:
        """Get current position in beats since master start time"""
        elapsed_time = time.time() - self.master_start_time
        return elapsed_time / self.beat_duration
    
    def _get_next_quantized_beat(self) -> float:
        """Get timestamp of next quantized beat"""
        current_beat = self._get_current_beat_position()
        quantize_interval = 1.0 / self.quantize_resolution
        
        # Round up to next quantization point
        next_quantized_beat = math.ceil(current_beat / quantize_interval) * quantize_interval
        
        # Convert back to timestamp
        return self.master_start_time + (next_quantized_beat * self.beat_duration)
    
    def _calculate_sync_delay(self) -> float:
        """Calculate delay until next quantized beat"""
        if not self.sync_enabled:
            return 0.0
        
        next_beat_time = self._get_next_quantized_beat()
        current_time = time.time()
        delay = max(0.0, next_beat_time - current_time)
        
        return delay
    
    def _sync_update_bpm(self, new_bpm: float):
        """Update BPM and recalculate beat timing"""
        self.current_bpm = new_bpm
        self.beat_duration = 60.0 / self.current_bpm
        print(f"🎵 BPM updated: {new_bpm:.1f} (beat duration: {self.beat_duration:.3f}s)")
    
    def _setup_osc_server(self):
        """Setup OSC server for control"""
        if not self.config.osc.enable_osc:
            return
            
        disp = dispatcher.Dispatcher()
        
        # Basic controls
        disp.map("/bpm", self.handle_bpm_change)
        disp.map("/crossfade", self.handle_crossfade)
        disp.map("/master_volume", self.handle_master_volume)
        disp.map("/key", self.handle_key_change)
        disp.map("/status", lambda unused_addr: self._show_status())
        disp.map("/random", lambda unused_addr: self._randomize_mix())
        
        # Memory management
        disp.map("/memory_status", lambda unused_addr: self._show_memory_status())
        disp.map("/memory_cleanup", lambda unused_addr: self._cleanup_memory())
        
        # Stem volume controls
        for stem in ['bass', 'drums', 'vocals', 'piano', 'other']:
            disp.map(f"/stem/{stem}", lambda unused_addr, vol, s=stem: self._set_stem_volume(s, vol))
        
        try:
            self.osc_server = ThreadingOSCUDPServer((self.config.osc.host, self.osc_port), disp)
            osc_thread = threading.Thread(target=self.osc_server.serve_forever, daemon=True)
            osc_thread.start()
            print(f"📡 OSC server started on {self.config.osc.host}:{self.osc_port}")
        except Exception as e:
            print(f"❌ Failed to start OSC server: {e}")
    
    def _smart_load_stem(self, song_identifier: str, stem_type: str, section: str = None) -> Optional[int]:
        """Smart load: only load stem if not already loaded"""
        song_index = self._find_song_by_identifier(song_identifier)
        if song_index is None:
            print(f"❌ Song not found: '{song_identifier}'")
            print(f"💡 Try a country name (albania, croatia) or song number (0, 1, 2...)")
            return None
            
        song = self.available_songs[song_index]
        if stem_type not in song['stems']:
            print(f"❌ Stem {stem_type} not found in {song['name']}")
            return None
        
        # Generate buffer ID
        buffer_id = self.next_synth_id
        self.next_synth_id += 1
        
        # Send load command to SuperCollider (smart loading server will handle it)
        stem_file = song['stems'][stem_type]
        stem_name = f"{song['name']}_{stem_type}"
        if section:
            stem_name += f"_{section}"
        
        try:
            self.sc_client.send_message("/load_buffer", [
                buffer_id,
                str(stem_file.absolute()),
                stem_name
            ])
            
            # Wait for buffer to load - longer wait for first buffer
            if buffer_id == 1000:
                time.sleep(2.0)  # Extra time for first buffer to avoid race condition
                # needed by python realtime engine (not in supercollider)
                print(f"⏳ Extra wait for first buffer {buffer_id}")
            else:
                time.sleep(1.0)  # Standard wait for subsequent buffers
            
            self.loaded_buffers.add(buffer_id)
            
            section_info = f" [{section}]" if section else ""
            print(f"📥 Smart loading: {stem_type}{section_info} from {song['name']} → buffer {buffer_id}")
            
            return buffer_id
            
        except Exception as e:
            print(f"❌ Error loading {stem_name}: {e}")
            return None
    
    def _smart_play_stem(self, buffer_id: int, song: dict, stem_type: str, section: str = None, 
                         sync_mode: str = "quantized", loop: bool = True):
        """Smart play: play stem with temporal synchronization options
        
        Args:
            sync_mode: "quantized" (wait for beat), "instant" (play immediately)
            loop: True for continuous looping, False for one-shot playback
        """
        try:
            # Calculate playback parameters
            playback_rate = self.current_bpm / song['bpm'] if song['bpm'] > 0 else 1.0
            volume = self.stem_volumes.get(stem_type, 0.8)
            
            # Section timing
            start_pos = 0.0
            if section and song['sections']:
                # Find section timing
                for sect in song['sections']:
                    if sect['label'].lower() == section.lower():
                        start_pos = sect['start']
                        break
            
            # Validate buffer ID before playing
            if not isinstance(buffer_id, int) or buffer_id < 1000:
                print(f"❌ Invalid buffer ID: {buffer_id}")
                return
            
            # Prepare message parameters
            message_params = [
                int(buffer_id),
                float(playback_rate),
                float(volume),
                int(loop),  # loop flag
                float(start_pos)
            ]
            
            # Handle synchronization modes
            if sync_mode == "quantized" and self.sync_enabled:
                sync_delay = self._calculate_sync_delay()
                if sync_delay > 0.01:  # Only delay if significant
                    # Schedule for next quantized beat
                    print(f"⏱️  Quantizing: buffer {buffer_id} in {sync_delay:.3f}s")
                    timer = threading.Timer(sync_delay, self._execute_play_command, 
                                          args=[message_params, buffer_id, song, stem_type, section])
                    timer.start()
                    return
            
            # Execute immediately (instant mode or no delay needed)
            self._execute_play_command(message_params, buffer_id, song, stem_type, section)
            
        except Exception as e:
            print(f"❌ Error preparing buffer {buffer_id}: {e}")
    
    def _execute_play_command(self, message_params: list, buffer_id: int, song: dict, 
                            stem_type: str, section: str = None):
        """Execute the actual play command with retry logic"""
        try:
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.sc_client.send_message("/play_stem", message_params)
                    break  # Success, exit retry loop
                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f"⚠️  OSC send attempt {attempt + 1} failed, retrying...")
                        time.sleep(0.5)
                    else:
                        raise e
            
            self.playing_stems.add(buffer_id)
            
            # Show playback info
            loop_info = "🔄" if message_params[3] else "🎯"
            section_info = f" from {message_params[4]:.1f}s [{section}]" if section else ""
            current_beat = self._get_current_beat_position()
            
            print(f"▶️  {loop_info} buffer {buffer_id}{section_info} | "
                  f"rate: {message_params[1]:.3f} | beat: {current_beat:.1f}")
            
        except Exception as e:
            print(f"❌ Error executing play command for buffer {buffer_id}: {e}")
    
    def _load_individual_stem(self, deck: str, song_identifier: str, stem_type: str, section: str = None):
        """Load and play individual stem with smart loading"""
        # Stop existing stem of this type in deck
        deck_stems = self.deck_a_stems if deck == 'A' else self.deck_b_stems
        
        if stem_type in deck_stems:
            old_buffer_id = deck_stems[stem_type]['buffer_id']
            self._stop_stem(old_buffer_id)
            del deck_stems[stem_type]
        
        # Smart load new stem
        buffer_id = self._smart_load_stem(song_identifier, stem_type, section)
        if buffer_id is None:
            return False
        
        song_index = self._find_song_by_identifier(song_identifier)
        song = self.available_songs[song_index]
        
        # Store deck configuration
        deck_stems[stem_type] = {
            'buffer_id': buffer_id,
            'song': song,
            'section': section
        }
        
        # Smart play with default quantized sync
        self._smart_play_stem(buffer_id, song, stem_type, section, sync_mode="quantized", loop=True)
        
        return True
    
    def _load_individual_sample(self, deck: str, song_identifier: str, stem_type: str, section: str = None):
        """Load and play individual sample instantly (no sync, no loop)"""
        # Don't stop existing stems for samples - they're additive
        
        # Smart load new sample  
        buffer_id = self._smart_load_stem(song_identifier, stem_type, section)
        if buffer_id is None:
            return False
        
        song_index = self._find_song_by_identifier(song_identifier)
        song = self.available_songs[song_index]
        
        # Play instantly without sync or looping (for samples/effects)
        self._smart_play_stem(buffer_id, song, stem_type, section, sync_mode="instant", loop=False)
        
        print(f"🎯 Sample fired: {stem_type} from {song['name']}")
        return True
    
    def _play_instant_stem(self, deck: str, song_identifier: str, stem_type: str, section: str = None):
        """Play stem instantly without quantization (for manual timing)"""
        # Stop existing stem of this type in deck
        deck_stems = self.deck_a_stems if deck == 'A' else self.deck_b_stems
        
        if stem_type in deck_stems:
            old_buffer_id = deck_stems[stem_type]['buffer_id']
            self._stop_stem(old_buffer_id)
            del deck_stems[stem_type]
        
        # Smart load new stem
        buffer_id = self._smart_load_stem(song_identifier, stem_type, section)
        if buffer_id is None:
            return False
        
        song_index = self._find_song_by_identifier(song_identifier)
        song = self.available_songs[song_index]
        
        # Store deck configuration
        deck_stems[stem_type] = {
            'buffer_id': buffer_id,
            'song': song,
            'section': section
        }
        
        # Play instantly with looping
        self._smart_play_stem(buffer_id, song, stem_type, section, sync_mode="instant", loop=True)
        
        return True
    
    def _stop_stem(self, buffer_id: int):
        """Stop and cleanup stem"""
        try:
            self.sc_client.send_message("/stop_stem", [buffer_id])
            self.playing_stems.discard(buffer_id)
            self.loaded_buffers.discard(buffer_id)
            print(f"⏹️  Stopped buffer {buffer_id}")
        except Exception as e:
            print(f"❌ Error stopping buffer {buffer_id}: {e}")
    
    def _set_stem_volume(self, stem_type: str, volume: float):
        """Set volume for stem type across both decks"""
        volume = max(0.0, min(1.0, volume))
        self.stem_volumes[stem_type] = volume
        
        # Update all active stems of this type
        for deck_stems in [self.deck_a_stems, self.deck_b_stems]:
            if stem_type in deck_stems:
                buffer_id = deck_stems[stem_type]['buffer_id']
                try:
                    self.sc_client.send_message("/stem_volume", [buffer_id, volume])
                except Exception as e:
                    print(f"❌ Error setting volume: {e}")
        
        print(f"🎚️  {stem_type.capitalize()} volume: {volume:.2f}")
    
    def _update_playback(self):
        """Update crossfade and BPM for all playing stems"""
        try:
            # Update crossfade
            deck_a_level = (1.0 - self.crossfade_position) * self.master_volume
            deck_b_level = self.crossfade_position * self.master_volume
            self.sc_client.send_message("/crossfade_levels", [deck_a_level, deck_b_level])
            
            # Update BPM for all playing stems (re-trigger playback)
            for deck_stems in [self.deck_a_stems, self.deck_b_stems]:
                for stem_type, stem_info in deck_stems.items():
                    buffer_id = stem_info['buffer_id']
                    song = stem_info['song']
                    section = stem_info['section']
                    self._smart_play_stem(buffer_id, song, stem_type, section)
                    
        except Exception as e:
            print(f"❌ Error updating playback: {e}")
    
    def _show_status(self):
        """Show current mixer and memory status"""
        print("\\n🎛️🧠 SMART LOADING STEM MIXER STATUS")
        print("=" * 50)
        print(f"🎵 BPM: {self.current_bpm:.1f}")
        print(f"🎚️  Crossfade: {self.crossfade_position:.2f}")
        print(f"🔊 Master Volume: {self.master_volume:.2f}")
        
        print(f"\\n💾 Memory Status:")
        print(f"  Loaded buffers: {len(self.loaded_buffers)}")
        print(f"  Playing stems: {len(self.playing_stems)}")
        
        for deck_name, deck_stems in [("A", self.deck_a_stems), ("B", self.deck_b_stems)]:
            print(f"\\n🎵 DECK {deck_name}:")
            if deck_stems:
                for stem_type, info in deck_stems.items():
                    section_info = f" [{info['section']}]" if info['section'] else ""
                    print(f"  {stem_type}: {info['song']['name']}{section_info} (buffer: {info['buffer_id']})")
            else:
                print("  (Empty)")
        
        print()
    
    def _show_memory_status(self):
        """Request memory status from SuperCollider"""
        try:
            self.sc_client.send_message("/get_status", [])
            print("📊 Requested memory status from SuperCollider")
        except Exception as e:
            print(f"❌ Error requesting status: {e}")
    
    def _cleanup_memory(self):
        """Request memory cleanup from SuperCollider"""
        try:
            self.sc_client.send_message("/memory_cleanup", [])
            print("🧹 Requested memory cleanup from SuperCollider")
        except Exception as e:
            print(f"❌ Error requesting cleanup: {e}")
    
    def _randomize_mix(self):
        """Create random mix with smart loading"""
        self.current_bpm = random.uniform(100, 150)
        self.crossfade_position = random.uniform(0.0, 1.0)
        
        if len(self.available_songs) >= 2:
            # Random stems from random songs
            stems_to_load = random.sample(['bass', 'drums', 'vocals', 'piano', 'other'], 
                                        random.randint(2, 4))
            
            for stem_type in stems_to_load:
                song_a = random.randint(0, len(self.available_songs) - 1)
                song_b = random.randint(0, len(self.available_songs) - 1)
                
                # Random sections if available
                section_a = None
                section_b = None
                
                if self.available_songs[song_a]['sections']:
                    section_a = random.choice(self.available_songs[song_a]['sections'])['label']
                
                if self.available_songs[song_b]['sections']:
                    section_b = random.choice(self.available_songs[song_b]['sections'])['label']
                
                self._load_individual_stem('A', song_a, stem_type, section_a)
                self._load_individual_stem('B', song_b, stem_type, section_b)
        
        print(f"🎲 Random smart mix: BPM {self.current_bpm:.0f}")
        self._update_playback()
    
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
    
    def _control_loop(self):
        """Smart loading control loop"""
        print("\\n💡 SMART LOADING COMMANDS:")
        print("=== BASIC CONTROLS ===")
        print("  bmp <value>           - Set BPM")
        print("  cross <0-1>           - Crossfade")  
        print("  songs                 - List songs")
        print("  status                - Show status")
        print("  memory                - Show SC memory status")
        print("  cleanup               - Cleanup unused memory")
        print("  quit                  - Exit")
        print()
        print("=== SMART STEM LOADING (Beat-Quantized) ===")
        print("  a.<stem> <country/id> - Load stem to deck A (quantized)")
        print("  b.<stem> <country/id> - Load stem to deck B (quantized)")
        print("  a.<stem>.<section> <country/id> - Load stem + section to deck A")
        print("  b.<stem>.<section> <country/id> - Load stem + section to deck B")
        print("  Examples: a.bass albania, b.vocals.chorus croatia, a.drums 2")
        print()
        print("=== INSTANT PLAYBACK ===")
        print("  instant.<stem> <country/id> - Play stem instantly (no quantization)")
        print("  sample.<stem> <country/id>  - Fire one-shot sample (no loop, instant)")
        print("  Examples: instant.bass denmark, sample.vocals albania, instant.drums 1")
        print()
        print("=== SYNC CONTROLS ===")
        print("  sync on/off           - Enable/disable beat quantization")
        print("  quantize <1|2|4|8>    - Set quantization resolution (beats)")
        print("  sync status           - Show synchronization status")
        print()
        print("=== VOLUME CONTROLS ===")
        print("  bass/drums/vocals/piano/other <0-1> - Set volume")
        print()
        print("=== OTHER ===")
        print("  random                - Random smart mix")
        print("  sections <country/id> - Show sections for song")
        print("  Examples: sections albania, sections 0")
        print()
        
        while self.running:
            try:
                cmd = input("🎛️🧠 > ").strip().lower()
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
                        print("❌ Invalid BPM")
                        
                elif command == "cross" and len(parts) == 2:
                    try:
                        pos = float(parts[1])
                        self.handle_crossfade(None, pos)
                    except ValueError:
                        print("❌ Invalid crossfade")
                        
                elif command == "status":
                    self._show_status()
                    
                elif command == "memory":
                    self._show_memory_status()
                    
                elif command == "cleanup":
                    self._cleanup_memory()
                    
                elif command == "songs":
                    print(f"\\n🎵 Available Songs ({len(self.available_songs)}):")
                    for i, song in enumerate(self.available_songs):
                        sections = len(song['sections'])
                        country = song.get('country', 'unknown').title()
                        print(f"  {i}: {song['name']} | Country: {country} | BPM: {song['bpm']:.0f} | Sections: {sections}")
                    print()
                    print("💡 Use country names or numbers: 'a.bass albania' or 'a.bass 0'")
                    
                elif command == "sections" and len(parts) == 2:
                    song_idx = self._find_song_by_identifier(parts[1])
                    if song_idx is not None:
                        song = self.available_songs[song_idx]
                        country = song.get('country', 'unknown').title()
                        print(f"\\n📊 Sections for {song['name']} ({country}):")
                        for section in song['sections']:
                            print(f"  {section['label']}: {section['start']:.1f}s - {section['end']:.1f}s")
                        print()
                    else:
                        print(f"❌ Song not found: '{parts[1]}'")
                        print("💡 Try a country name (albania, croatia) or song number (0, 1, 2...)")
                
                elif command == "sync" and len(parts) == 2:
                    # Sync control commands
                    if parts[1] == "on":
                        self.sync_enabled = True
                        print("🔄 Beat quantization enabled")
                    elif parts[1] == "off":
                        self.sync_enabled = False
                        print("⏩ Beat quantization disabled")
                    elif parts[1] == "status":
                        status = "enabled" if self.sync_enabled else "disabled"
                        print(f"🔄 Sync: {status}")
                        print(f"⏱️  BPM: {self.current_bpm:.1f}")
                        print(f"🎯 Quantize: {self.quantize_resolution} beats")
                        if self.master_start_time:
                            current_beat = self._get_current_beat_position()
                            print(f"📍 Current beat: {current_beat:.2f}")
                    else:
                        print("❌ Use: sync on/off/status")
                
                elif command == "quantize" and len(parts) == 2:
                    try:
                        resolution = int(parts[1])
                        if resolution in [1, 2, 4, 8]:
                            self.quantize_resolution = resolution
                            print(f"🎯 Quantization set to {resolution} beats")
                        else:
                            print("❌ Use: quantize 1/2/4/8")
                    except ValueError:
                        print("❌ Invalid quantization value")
                
                elif command.startswith("instant.") and len(parts) == 2:
                    # Instant playback commands
                    stem_type = command.split(".", 1)[1]
                    song_identifier = parts[1]
                    # Default to deck A for instant commands
                    self._play_instant_stem('A', song_identifier, stem_type)
                
                elif command.startswith("sample.") and len(parts) == 2:
                    # Sample (one-shot) commands
                    stem_type = command.split(".", 1)[1]
                    song_identifier = parts[1]
                    # Default to deck A for sample commands
                    self._load_individual_sample('A', song_identifier, stem_type)
                
                elif "." in command and len(parts) == 2:
                    # Smart stem loading
                    deck_parts = command.split(".")
                    song_identifier = parts[1]
                    
                    if len(deck_parts) == 2:
                        # Format: a.bass albania (or a.bass 2)
                        deck, stem = deck_parts
                        self._load_individual_stem(deck.upper(), song_identifier, stem)
                    elif len(deck_parts) == 3:
                        # Format: a.bass.chorus albania (or a.bass.chorus 2)  
                        deck, stem, section = deck_parts
                        self._load_individual_stem(deck.upper(), song_identifier, stem, section)
                        
                elif command in self.stem_volumes and len(parts) == 2:
                    try:
                        volume = float(parts[1])
                        self._set_stem_volume(command, volume)
                    except ValueError:
                        print("❌ Invalid volume")
                        
                elif command == "random":
                    self._randomize_mix()
                    
                else:
                    print("❌ Unknown command")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Error: {e}")
        
        self.stop()
    
    def start(self):
        """Start the smart mixer"""
        print("🚀 Starting Smart Loading Stem Mixer...")
        
        # Test SuperCollider connection
        try:
            self.sc_client.send_message("/test_tone", [440, 0.5])
            print("✅ SuperCollider connection test sent")
        except Exception as e:
            print(f"⚠️  Could not connect to SuperCollider: {e}")
        
        self.control_thread.start()
        
        try:
            self.control_thread.join()
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Stop and cleanup - similar to dj_plan_executor.py approach"""
        print("\\n🛑 Stopping Smart Loading Mixer...")
        self.running = False
        
        # Stop all audio and free memory (like dj_plan_executor.py)
        try:
            self.sc_client.send_message("/mixer_cleanup", [])
            print("⏹️  Stopped all audio and freed memory")
        except Exception as e:
            print(f"❌ Error stopping: {e}")
        
        # Clear our tracking (like dj_plan_executor.py clears loaded_buffers)
        self.playing_stems.clear()
        self.loaded_buffers.clear()
        self.deck_a_stems.clear()
        self.deck_b_stems.clear()
        
        if self.osc_server:
            self.osc_server.shutdown()
        
        print("👋 Smart mixer stopped!")

def main():
    mixer = SmartSuperColliderStemMixer()
    mixer.start()

if __name__ == "__main__":
    print("Works with supercollider_audio_server_minimal.scd")
    main()
