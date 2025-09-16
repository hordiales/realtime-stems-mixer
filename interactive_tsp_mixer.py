#!/usr/bin/env python3
"""
Interactive TSP AutoDJ with Real-time Stem Swapping
Allows dynamic stem replacement during playback with key/BPM adjustment
"""

import numpy as np
import librosa
import soundfile as sf
import pyaudio
from threading import Thread, Event, Lock
import time
import queue
from pathlib import Path
from typing import List, Optional, Tuple, Dict
import sys
import select
import threading
from dataclasses import dataclass, field
from tsp_autodj import TSPAutoDJ, SongMetadata, CamelotWheel, BPMDistance

@dataclass
class StemInfo:
    """Information about an individual stem"""
    song_name: str
    stem_type: str  # bass, drums, vocals, piano, other
    file_path: str
    bpm: float
    key: str
    duration: float
    energy: float

@dataclass
class ActiveStem:
    """Currently active stem with processing info"""
    stem_info: StemInfo
    audio_data: np.ndarray
    original_bpm: float
    target_bpm: float
    original_key: str
    target_key: str
    volume: float = 1.0
    pitch_shift: float = 0.0  # semitones
    tempo_ratio: float = 1.0

class StemLibrary:
    """Library of all available stems from all songs"""
    
    def __init__(self, songs: List[SongMetadata]):
        self.stems: Dict[str, List[StemInfo]] = {
            'bass': [], 'drums': [], 'vocals': [], 'piano': [], 'other': []
        }
        self.song_stems: Dict[str, Dict[str, StemInfo]] = {}
        self._build_library(songs)
    
    def _build_library(self, songs: List[SongMetadata]):
        """Build library from all analyzed songs"""
        print("🏗️  Building stem library...")
        
        for song in songs:
            song_dir = Path(song.path)
            self.song_stems[song.name] = {}
            
            for stem_type in self.stems.keys():
                stem_file = song_dir / f"{stem_type}.wav"
                if stem_file.exists():
                    stem_info = StemInfo(
                        song_name=song.name,
                        stem_type=stem_type,
                        file_path=str(stem_file),
                        bpm=song.bpm,
                        key=song.key,
                        duration=song.duration,
                        energy=song.energy
                    )
                    
                    self.stems[stem_type].append(stem_info)
                    self.song_stems[song.name][stem_type] = stem_info
        
        # Show library stats
        for stem_type, stem_list in self.stems.items():
            print(f"  {stem_type.upper()}: {len(stem_list)} available")
    
    def find_compatible_stems(self, stem_type: str, target_key: str, target_bpm: float, 
                            max_key_distance: float = 0.5, max_bpm_ratio: float = 0.3) -> List[StemInfo]:
        """Find stems compatible with target key and BPM"""
        compatible = []
        
        for stem in self.stems[stem_type]:
            # Check key compatibility
            key_dist = CamelotWheel.key_distance(stem.key, target_key)
            if key_dist > max_key_distance:
                continue
                
            # Check BPM compatibility
            bpm_dist = BPMDistance.bpm_distance(stem.bpm, target_bpm)
            if bpm_dist > max_bpm_ratio:
                continue
                
            compatible.append(stem)
        
        # Sort by compatibility (key + BPM)
        compatible.sort(key=lambda s: (
            CamelotWheel.key_distance(s.key, target_key) * 0.6 +
            BPMDistance.bpm_distance(s.bpm, target_bpm) * 0.4
        ))
        
        return compatible
    
    def get_stem_by_song(self, song_name: str, stem_type: str) -> Optional[StemInfo]:
        """Get specific stem from specific song"""
        return self.song_stems.get(song_name, {}).get(stem_type)
    
    def list_songs(self) -> List[str]:
        """Get list of all song names"""
        return list(self.song_stems.keys())
    
    def list_stems_for_song(self, song_name: str) -> List[str]:
        """Get available stem types for a song"""
        return list(self.song_stems.get(song_name, {}).keys())

class RealTimeAudioProcessor:
    """Real-time audio processing for pitch and tempo adjustment"""
    
    @staticmethod
    def pitch_shift_audio(audio: np.ndarray, semitones: float, sr: int = 44100) -> np.ndarray:
        """Pitch shift audio by semitones"""
        if semitones == 0:
            return audio
        
        # Use librosa for pitch shifting
        if audio.ndim == 1:
            shifted = librosa.effects.pitch_shift(audio, sr=sr, n_steps=semitones)
            return np.stack([shifted, shifted]).T
        else:
            # Process each channel separately
            left = librosa.effects.pitch_shift(audio[:, 0], sr=sr, n_steps=semitones)
            right = librosa.effects.pitch_shift(audio[:, 1], sr=sr, n_steps=semitones)
            return np.stack([left, right]).T
    
    @staticmethod
    def time_stretch_audio(audio: np.ndarray, ratio: float) -> np.ndarray:
        """Time stretch audio by ratio (1.0 = no change, 2.0 = double speed)"""
        if ratio == 1.0:
            return audio
        
        if audio.ndim == 1:
            stretched = librosa.effects.time_stretch(audio, rate=ratio)
            return np.stack([stretched, stretched]).T
        else:
            # Process each channel separately  
            left = librosa.effects.time_stretch(audio[:, 0], rate=ratio)
            right = librosa.effects.time_stretch(audio[:, 1], rate=ratio)
            return np.stack([left, right]).T
    
    @staticmethod
    def calculate_pitch_shift_for_key(from_key: str, to_key: str) -> float:
        """Calculate pitch shift in semitones to go from one key to another"""
        if from_key == to_key:
            return 0.0
        
        # Simplified key to semitone mapping (Camelot wheel)
        key_to_semitone = {
            '1A': 0, '1B': 3, '2A': 7, '2B': 10, '3A': 2, '3B': 5,
            '4A': 9, '4B': 0, '5A': 4, '5B': 7, '6A': 11, '6B': 2,
            '7A': 6, '7B': 9, '8A': 1, '8B': 4, '9A': 8, '9B': 11,
            '10A': 3, '10B': 6, '11A': 10, '11B': 1, '12A': 5, '12B': 8
        }
        
        from_semitone = key_to_semitone.get(from_key, 0)
        to_semitone = key_to_semitone.get(to_key, 0)
        
        # Calculate shortest path (considering octave wrapping)
        diff = (to_semitone - from_semitone) % 12
        if diff > 6:
            diff -= 12
            
        return diff

class InteractiveMixer:
    """Interactive mixer with real-time stem swapping"""
    
    def __init__(self, sample_rate: int = 44100, chunk_size: int = 1024):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.audio = pyaudio.PyAudio()
        self.stream = None
        
        # Active stems (one per type)
        self.active_stems: Dict[str, Optional[ActiveStem]] = {
            'bass': None, 'drums': None, 'vocals': None, 'piano': None, 'other': None
        }
        
        # Audio buffers and playback
        self.playback_position = 0
        self.is_playing = False
        self.master_volume = 0.8
        
        # Threading and synchronization
        self.audio_lock = Lock()
        self.command_queue = queue.Queue()
        self.current_song_info: Optional[SongMetadata] = None
        
        # Processing
        self.processor = RealTimeAudioProcessor()
    
    def setup_stream(self) -> bool:
        """Initialize audio output stream"""
        try:
            self.stream = self.audio.open(
                format=pyaudio.paFloat32,
                channels=2,
                rate=self.sample_rate,
                output=True,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._audio_callback
            )
            return True
        except Exception as e:
            print(f"❌ Audio setup error: {e}")
            return False
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Real-time audio callback with stem mixing"""
        with self.audio_lock:
            try:
                output = self._mix_stems(frame_count)
                self.playback_position += frame_count
                return (output.tobytes(), pyaudio.paContinue)
            except Exception as e:
                print(f"⚠️  Audio callback error: {e}")
                return (np.zeros((frame_count, 2), dtype=np.float32).tobytes(), pyaudio.paContinue)
    
    def _mix_stems(self, frame_count: int) -> np.ndarray:
        """Mix all active stems into output buffer"""
        output = np.zeros((frame_count, 2), dtype=np.float32)
        
        if not self.is_playing:
            return output
        
        # Process command queue
        self._process_commands()
        
        # Mix each active stem
        for stem_type, active_stem in self.active_stems.items():
            if active_stem is None:
                continue
                
            try:
                # Get audio chunk from stem
                stem_chunk = self._get_stem_chunk(active_stem, frame_count)
                if stem_chunk is not None:
                    # Apply volume and mix
                    output += stem_chunk * active_stem.volume
            except Exception as e:
                print(f"⚠️  Error mixing {stem_type}: {e}")
        
        # Apply master volume and soft limiting
        output *= self.master_volume
        output = np.tanh(output * 0.95) * 0.95
        
        return output
    
    def _get_stem_chunk(self, active_stem: ActiveStem, frame_count: int) -> Optional[np.ndarray]:
        """Get audio chunk from active stem with position tracking"""
        audio_data = active_stem.audio_data
        
        if self.playback_position >= len(audio_data):
            return None
        
        end_pos = min(self.playback_position + frame_count, len(audio_data))
        chunk = audio_data[self.playback_position:end_pos]
        
        # Pad with zeros if needed
        if len(chunk) < frame_count:
            padding = np.zeros((frame_count - len(chunk), 2), dtype=np.float32)
            chunk = np.vstack([chunk, padding])
        
        return chunk
    
    def _process_commands(self):
        """Process queued commands"""
        while not self.command_queue.empty():
            try:
                command = self.command_queue.get_nowait()
                self._execute_command(command)
            except queue.Empty:
                break
    
    def _execute_command(self, command: dict):
        """Execute a mixer command"""
        cmd_type = command.get('type')
        
        if cmd_type == 'swap_stem':
            self._swap_stem(
                command['stem_type'],
                command['stem_info'],
                command.get('target_key'),
                command.get('target_bpm')
            )
        elif cmd_type == 'set_volume':
            self._set_stem_volume(command['stem_type'], command['volume'])
        elif cmd_type == 'mute_stem':
            self._mute_stem(command['stem_type'])
        elif cmd_type == 'unmute_stem':
            self._unmute_stem(command['stem_type'])
    
    def _swap_stem(self, stem_type: str, stem_info: StemInfo, target_key: str = None, target_bpm: float = None):
        """Swap active stem with new one"""
        try:
            # Load new stem audio
            audio, sr = librosa.load(stem_info.file_path, sr=self.sample_rate, mono=False)
            
            # Ensure stereo
            if audio.ndim == 1:
                audio = np.stack([audio, audio])
            elif audio.shape[0] == 1:
                audio = np.vstack([audio, audio])
            
            # Transpose to (samples, channels)
            audio = audio.T.astype(np.float32)
            
            # Calculate adjustments
            target_key = target_key or (self.current_song_info.key if self.current_song_info else stem_info.key)
            target_bpm = target_bpm or (self.current_song_info.bpm if self.current_song_info else stem_info.bpm)
            
            pitch_shift = self.processor.calculate_pitch_shift_for_key(stem_info.key, target_key)
            tempo_ratio = target_bpm / stem_info.bpm if stem_info.bpm > 0 else 1.0
            
            # Apply pitch shift
            if pitch_shift != 0:
                audio = self.processor.pitch_shift_audio(audio, pitch_shift, sr)
            
            # Apply time stretch
            if tempo_ratio != 1.0:
                audio = self.processor.time_stretch_audio(audio, tempo_ratio)
            
            # Create active stem
            active_stem = ActiveStem(
                stem_info=stem_info,
                audio_data=audio,
                original_bpm=stem_info.bpm,
                target_bpm=target_bpm,
                original_key=stem_info.key,
                target_key=target_key,
                pitch_shift=pitch_shift,
                tempo_ratio=tempo_ratio
            )
            
            # Replace active stem
            self.active_stems[stem_type] = active_stem
            
            print(f"🔄 Swapped {stem_type}: {stem_info.song_name}")
            print(f"   Key: {stem_info.key} → {target_key} ({pitch_shift:+.1f} semitones)")
            print(f"   BPM: {stem_info.bpm:.1f} → {target_bpm:.1f} ({tempo_ratio:.2f}x)")
            
        except Exception as e:
            print(f"❌ Error swapping {stem_type}: {e}")
    
    def _set_stem_volume(self, stem_type: str, volume: float):
        """Set volume for specific stem"""
        if self.active_stems[stem_type]:
            self.active_stems[stem_type].volume = max(0.0, min(2.0, volume))
            print(f"🔊 {stem_type.upper()} volume: {volume:.2f}")
    
    def _mute_stem(self, stem_type: str):
        """Mute specific stem"""
        if self.active_stems[stem_type]:
            self.active_stems[stem_type].volume = 0.0
            print(f"🔇 {stem_type.upper()} muted")
    
    def _unmute_stem(self, stem_type: str):
        """Unmute specific stem"""
        if self.active_stems[stem_type]:
            self.active_stems[stem_type].volume = 1.0
            print(f"🔊 {stem_type.upper()} unmuted")
    
    def queue_command(self, command: dict):
        """Queue command for execution in audio thread"""
        self.command_queue.put(command)
    
    def load_song(self, song: SongMetadata, stem_library: StemLibrary):
        """Load all stems of a song"""
        self.current_song_info = song
        self.playback_position = 0
        
        print(f"🎵 Loading: {song.name}")
        print(f"   Key: {song.key}, BPM: {song.bpm:.1f}")
        
        # Load all available stems
        for stem_type in self.active_stems.keys():
            stem_info = stem_library.get_stem_by_song(song.name, stem_type)
            if stem_info:
                self._swap_stem(stem_type, stem_info, song.key, song.bpm)
    
    def start_playback(self):
        """Start audio playback"""
        self.is_playing = True
        if self.stream:
            self.stream.start_stream()
    
    def stop_playback(self):
        """Stop audio playback"""
        self.is_playing = False
        if self.stream:
            self.stream.stop_stream()
    
    def get_status(self) -> dict:
        """Get current mixer status"""
        active_stems = {k: v.stem_info.song_name if v else None 
                       for k, v in self.active_stems.items()}
        
        return {
            'playing': self.is_playing,
            'current_song': self.current_song_info.name if self.current_song_info else None,
            'position': self.playback_position / self.sample_rate,
            'active_stems': active_stems
        }
    
    def cleanup(self):
        """Cleanup audio resources"""
        self.stop_playback()
        if self.stream:
            self.stream.close()
        self.audio.terminate()

class InteractiveCLI:
    """Command line interface for interactive mixing"""
    
    def __init__(self, mixer: InteractiveMixer, stem_library: StemLibrary):
        self.mixer = mixer
        self.stem_library = stem_library
        self.running = False
        self.input_thread = None
    
    def start(self):
        """Start interactive CLI"""
        self.running = True
        self.input_thread = Thread(target=self._input_loop, daemon=True)
        self.input_thread.start()
        
        self._show_help()
    
    def stop(self):
        """Stop interactive CLI"""
        self.running = False
    
    def _input_loop(self):
        """Main input processing loop"""
        while self.running:
            try:
                command = input("🎛️  > ").strip().lower()
                if command:
                    self._process_command(command)
            except (KeyboardInterrupt, EOFError):
                print("\n👋 Exiting...")
                self.running = False
                break
            except Exception as e:
                print(f"⚠️  Command error: {e}")
    
    def _process_command(self, command: str):
        """Process CLI command"""
        parts = command.split()
        if not parts:
            return
        
        cmd = parts[0]
        
        if cmd == 'help' or cmd == 'h':
            self._show_help()
        
        elif cmd == 'status' or cmd == 's':
            self._show_status()
        
        elif cmd == 'list' or cmd == 'l':
            if len(parts) > 1:
                self._list_items(parts[1])
            else:
                self._list_items('songs')
        
        elif cmd == 'swap':
            if len(parts) >= 3:
                self._swap_stem_command(parts[1], parts[2], parts[3:])
            else:
                print("Usage: swap <stem_type> <song_name> [options]")
        
        elif cmd == 'volume' or cmd == 'vol':
            if len(parts) == 3:
                self._set_volume_command(parts[1], parts[2])
            else:
                print("Usage: volume <stem_type> <volume>")
        
        elif cmd == 'mute' or cmd == 'm':
            if len(parts) == 2:
                self._mute_command(parts[1])
            else:
                print("Usage: mute <stem_type>")
        
        elif cmd == 'unmute' or cmd == 'u':
            if len(parts) == 2:
                self._unmute_command(parts[1])
            else:
                print("Usage: unmute <stem_type>")
        
        elif cmd == 'find':
            if len(parts) >= 2:
                self._find_stems_command(parts[1], parts[2:])
            else:
                print("Usage: find <stem_type> [key] [bpm]")
        
        elif cmd == 'play':
            self.mixer.start_playback()
            print("▶️  Playback started")
        
        elif cmd == 'stop':
            self.mixer.stop_playback() 
            print("⏹️  Playback stopped")
        
        elif cmd == 'quit' or cmd == 'q' or cmd == 'exit':
            self.running = False
        
        else:
            print(f"❓ Unknown command: {cmd}. Type 'help' for available commands.")
    
    def _show_help(self):
        """Show help text"""
        print("\n🎛️  INTERACTIVE TSP MIXER COMMANDS:")
        print("=" * 50)
        print("📊 INFO:")
        print("  help, h          - Show this help")
        print("  status, s        - Show current mixer status")
        print("  list songs       - List all available songs")
        print("  list <stem_type> - List stems of type (bass, drums, vocals, piano, other)")
        print()
        print("🎵 PLAYBACK:")
        print("  play             - Start playback")
        print("  stop             - Stop playback") 
        print()
        print("🔄 STEM SWAPPING:")
        print("  swap <stem> <song>        - Replace stem with one from another song")
        print("  find <stem> [key] [bpm]   - Find compatible stems")
        print("  Examples:")
        print("    swap bass albania        - Use bass from Albania song")
        print("    swap drums croatia       - Use drums from Croatia song")
        print("    find vocals 4A 120       - Find vocals in key 4A around 120 BPM")
        print()
        print("🔊 VOLUME:")
        print("  volume <stem> <vol>  - Set stem volume (0.0-2.0)")
        print("  mute <stem>         - Mute specific stem")
        print("  unmute <stem>       - Unmute specific stem")
        print()
        print("🚪 EXIT:")
        print("  quit, q, exit       - Exit mixer")
        print("=" * 50)
    
    def _show_status(self):
        """Show current mixer status"""
        status = self.mixer.get_status()
        
        print(f"\n📊 MIXER STATUS:")
        print(f"  Current Song: {status['current_song'] or 'None'}")
        print(f"  Playing: {'Yes' if status['playing'] else 'No'}")
        print(f"  Position: {status['position']:.1f}s")
        print(f"\n🎵 ACTIVE STEMS:")
        
        for stem_type, source_song in status['active_stems'].items():
            volume = ""
            if self.mixer.active_stems[stem_type]:
                vol = self.mixer.active_stems[stem_type].volume
                volume = f" (vol: {vol:.2f})"
            
            print(f"  {stem_type.upper():6}: {source_song or 'None'}{volume}")
    
    def _list_items(self, item_type: str):
        """List available items"""
        if item_type == 'songs':
            songs = self.stem_library.list_songs()
            print(f"\n🎵 AVAILABLE SONGS ({len(songs)}):")
            for i, song in enumerate(songs, 1):
                print(f"  {i:2d}. {song}")
        
        elif item_type in ['bass', 'drums', 'vocals', 'piano', 'other']:
            stems = self.stem_library.stems[item_type]
            print(f"\n🎶 AVAILABLE {item_type.upper()} STEMS ({len(stems)}):")
            for stem in stems:
                print(f"  {stem.song_name} (Key: {stem.key}, BPM: {stem.bpm:.1f})")
        
        else:
            print("❓ Available lists: songs, bass, drums, vocals, piano, other")
    
    def _swap_stem_command(self, stem_type: str, song_identifier: str, options: list):
        """Handle stem swap command"""
        if stem_type not in ['bass', 'drums', 'vocals', 'piano', 'other']:
            print(f"❓ Invalid stem type. Use: bass, drums, vocals, piano, other")
            return
        
        # Find matching song
        songs = self.stem_library.list_songs()
        matching_songs = [s for s in songs if song_identifier.lower() in s.lower()]
        
        if not matching_songs:
            print(f"❌ No songs found matching '{song_identifier}'")
            return
        
        if len(matching_songs) > 1:
            print(f"🎯 Multiple matches found:")
            for song in matching_songs[:5]:
                print(f"  {song}")
            song_name = matching_songs[0]
            print(f"Using first match: {song_name}")
        else:
            song_name = matching_songs[0]
        
        # Get stem info
        stem_info = self.stem_library.get_stem_by_song(song_name, stem_type)
        if not stem_info:
            print(f"❌ No {stem_type} stem found in {song_name}")
            return
        
        # Parse options (key, bpm)
        target_key = None
        target_bpm = None
        
        for option in options:
            if option.upper().endswith(('A', 'B')) and len(option) <= 3:
                target_key = option.upper()
            elif option.replace('.', '').isdigit():
                target_bpm = float(option)
        
        # Queue swap command
        command = {
            'type': 'swap_stem',
            'stem_type': stem_type,
            'stem_info': stem_info,
            'target_key': target_key,
            'target_bpm': target_bpm
        }
        
        self.mixer.queue_command(command)
    
    def _set_volume_command(self, stem_type: str, volume_str: str):
        """Handle volume command"""
        if stem_type not in ['bass', 'drums', 'vocals', 'piano', 'other']:
            print(f"❓ Invalid stem type. Use: bass, drums, vocals, piano, other")
            return
        
        try:
            volume = float(volume_str)
            command = {
                'type': 'set_volume',
                'stem_type': stem_type,
                'volume': volume
            }
            self.mixer.queue_command(command)
        except ValueError:
            print(f"❌ Invalid volume value: {volume_str}")
    
    def _mute_command(self, stem_type: str):
        """Handle mute command"""
        if stem_type not in ['bass', 'drums', 'vocals', 'piano', 'other']:
            print(f"❓ Invalid stem type. Use: bass, drums, vocals, piano, other")
            return
        
        command = {'type': 'mute_stem', 'stem_type': stem_type}
        self.mixer.queue_command(command)
    
    def _unmute_command(self, stem_type: str):
        """Handle unmute command"""
        if stem_type not in ['bass', 'drums', 'vocals', 'piano', 'other']:
            print(f"❓ Invalid stem type. Use: bass, drums, vocals, piano, other")  
            return
        
        command = {'type': 'unmute_stem', 'stem_type': stem_type}
        self.mixer.queue_command(command)
    
    def _find_stems_command(self, stem_type: str, criteria: list):
        """Handle find stems command"""
        if stem_type not in ['bass', 'drums', 'vocals', 'piano', 'other']:
            print(f"❓ Invalid stem type. Use: bass, drums, vocals, piano, other")
            return
        
        # Parse criteria
        target_key = None
        target_bpm = None
        
        for criterion in criteria:
            if criterion.upper().endswith(('A', 'B')) and len(criterion) <= 3:
                target_key = criterion.upper()
            elif criterion.replace('.', '').isdigit():
                target_bpm = float(criterion)
        
        # Use current song info as defaults
        if not target_key and self.mixer.current_song_info:
            target_key = self.mixer.current_song_info.key
        if not target_bpm and self.mixer.current_song_info:
            target_bpm = self.mixer.current_song_info.bpm
        
        if not target_key or not target_bpm:
            print("❌ Need target key and BPM. Example: find vocals 4A 120")
            return
        
        # Find compatible stems
        compatible = self.stem_library.find_compatible_stems(stem_type, target_key, target_bpm)
        
        print(f"\n🔍 COMPATIBLE {stem_type.upper()} STEMS for {target_key} @ {target_bpm:.1f} BPM:")
        if not compatible:
            print("  No compatible stems found")
        else:
            for stem in compatible[:10]:  # Show top 10
                key_dist = CamelotWheel.key_distance(stem.key, target_key)
                bpm_dist = BPMDistance.bpm_distance(stem.bpm, target_bpm)
                compatibility = 1.0 - (key_dist * 0.6 + bpm_dist * 0.4)
                
                print(f"  {stem.song_name} (Key: {stem.key}, BPM: {stem.bpm:.1f}) - {compatibility:.1%}")

class InteractiveTSPMixer(TSPAutoDJ):
    """Interactive TSP mixer with real-time stem swapping"""
    
    def __init__(self, stems_dir: str = "stems"):
        super().__init__(stems_dir)
        self.mixer = InteractiveMixer()
        self.stem_library = None
        self.cli = None
    
    def start_interactive_session(self):
        """Start interactive mixing session"""
        print("🎯 Interactive TSP Mixer with Real-time Stem Swapping")
        print("=" * 60)
        
        # Analyze songs and build tour
        if not self.analyze_and_plan_tour():
            return
        
        # Build stem library
        self.stem_library = StemLibrary(self.songs)
        
        # Setup audio
        if not self.mixer.setup_stream():
            print("❌ Failed to setup audio")
            return
        
        # Start with first song in tour
        if self.tour:
            first_song = self.songs[self.tour[0]]
            self.mixer.load_song(first_song, self.stem_library)
        
        # Start CLI
        self.cli = InteractiveCLI(self.mixer, self.stem_library)
        self.cli.start()
        
        print(f"\n🎵 Loaded first song: {first_song.name}")
        print("🎛️  Interactive mixer ready!")
        print("Type 'help' for commands, 'play' to start, 'quit' to exit")
        
        try:
            # Keep running until CLI stops
            while self.cli.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n👋 Stopping mixer...")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Cleanup resources"""
        if self.cli:
            self.cli.stop()
        if self.mixer:
            self.mixer.cleanup()

def main():
    """Main interactive TSP mixer"""
    mixer = InteractiveTSPMixer()
    mixer.start_interactive_session()

if __name__ == "__main__":
    main()