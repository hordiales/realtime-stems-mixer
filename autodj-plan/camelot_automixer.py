#!/usr/bin/env python3
"""
Camelot Wheel Automixer
Advanced harmonic mixing system using Camelot Wheel for intelligent stem selection.
Automatically mixes vocals, bass, and piano using harmonic compatibility.
Drums are considered harmonically neutral and can work with any key.
"""

import json
import random
import time
import threading
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from pythonosc import udp_client

# Add parent directory to path for config_loader import
sys.path.append(str(Path(__file__).parent.parent))
from config_loader import ConfigLoader, MixerConfig

class CamelotWheel:
    """Camelot Wheel implementation for harmonic mixing"""
    
    # Camelot Wheel mapping: Key -> (Major, Minor)
    WHEEL = {
        1: ('C', 'Am'),    # 1A = Am, 1B = C
        2: ('G', 'Em'),    # 2A = Em, 2B = G  
        3: ('D', 'Bm'),    # 3A = Bm, 3B = D
        4: ('A', 'F#m'),   # 4A = F#m, 4B = A
        5: ('E', 'C#m'),   # 5A = C#m, 5B = E
        6: ('B', 'G#m'),   # 6A = G#m, 6B = B
        7: ('F#', 'D#m'),  # 7A = D#m, 7B = F#
        8: ('Db', 'Bbm'),  # 8A = Bbm, 8B = Db
        9: ('Ab', 'Fm'),   # 9A = Fm, 9B = Ab
        10: ('Eb', 'Cm'),  # 10A = Cm, 10B = Eb
        11: ('Bb', 'Gm'),  # 11A = Gm, 11B = Bb
        12: ('F', 'Dm')    # 12A = Dm, 12B = F
    }
    
    # Reverse mapping for quick lookup
    KEY_TO_CAMELOT = {}
    for number, (major, minor) in WHEEL.items():
        KEY_TO_CAMELOT[major] = f"{number}B"
        KEY_TO_CAMELOT[minor] = f"{number}A"
    
    @classmethod
    def get_camelot_code(cls, key: str) -> Optional[str]:
        """Convert musical key to Camelot code"""
        # Normalize key input
        key = key.strip()
        
        # Handle various key formats
        if key in cls.KEY_TO_CAMELOT:
            return cls.KEY_TO_CAMELOT[key]
        
        # Try with 'm' suffix for minor
        if key.endswith('m') and key in cls.KEY_TO_CAMELOT:
            return cls.KEY_TO_CAMELOT[key]
            
        # Try adding 'm' for minor keys
        if key + 'm' in cls.KEY_TO_CAMELOT:
            return cls.KEY_TO_CAMELOT[key + 'm']
        
        return None
    
    @classmethod
    def get_compatible_keys(cls, key: str) -> List[str]:
        """Get harmonically compatible keys using Camelot Wheel rules"""
        camelot = cls.get_camelot_code(key)
        if not camelot:
            return []
        
        # Parse Camelot code (e.g., "1A" -> number=1, mode="A")
        number = int(camelot[:-1])
        mode = camelot[-1]
        
        compatible = []
        
        # Rule 1: Same number, different mode (relative major/minor)
        opposite_mode = "A" if mode == "B" else "B"
        compatible.append(f"{number}{opposite_mode}")
        
        # Rule 2: Adjacent numbers, same mode (±1 on wheel)
        prev_num = 12 if number == 1 else number - 1
        next_num = 1 if number == 12 else number + 1
        compatible.extend([f"{prev_num}{mode}", f"{next_num}{mode}"])
        
        # Rule 3: Perfect fifth (±7 positions, same mode)
        fifth_up = (number + 6) % 12 + 1  # +7 but 0-indexed
        fifth_down = (number - 8) % 12 + 1  # -7 but 0-indexed  
        compatible.extend([f"{fifth_up}{mode}", f"{fifth_down}{mode}"])
        
        # Convert back to musical keys
        result_keys = []
        for code in compatible:
            num = int(code[:-1])
            m = code[-1]
            if num in cls.WHEEL:
                major, minor = cls.WHEEL[num]
                key_name = major if m == "B" else minor
                result_keys.append(key_name)
        
        return result_keys
    
    @classmethod
    def calculate_harmony_score(cls, key1: str, key2: str) -> float:
        """Calculate harmonic compatibility score (0.0 - 1.0)"""
        if key1 == key2:
            return 1.0
        
        compatible_keys = cls.get_compatible_keys(key1)
        if key2 in compatible_keys:
            # Different weights for different compatibility types
            camelot1 = cls.get_camelot_code(key1)
            camelot2 = cls.get_camelot_code(key2)
            
            if camelot1 and camelot2:
                num1, mode1 = int(camelot1[:-1]), camelot1[-1]
                num2, mode2 = int(camelot2[:-1]), camelot2[-1]
                
                # Same number, different mode (relative major/minor) = 0.9
                if num1 == num2 and mode1 != mode2:
                    return 0.9
                
                # Adjacent numbers = 0.8
                if abs(num1 - num2) == 1 or abs(num1 - num2) == 11:  # Handle wrap-around
                    return 0.8
                
                # Perfect fifth = 0.7
                if abs(num1 - num2) == 7 or abs(num1 - num2) == 5:  # Handle wrap-around
                    return 0.7
        
        return 0.0  # Not compatible

class CamelotAutomixer:
    """Intelligent automixer using Camelot Wheel harmonic theory"""
    
    def __init__(self, stems_dir: str = "../stems", structures_dir: str = "../song-structures",
                 sc_host: str = "localhost", sc_port: int = 57120,
                 config_file: str = "mixer_config.json"):
        
        # Load configuration
        self.config_loader = ConfigLoader(config_file)
        self.config = self.config_loader.load_config()
        
        # Audio server connection
        self.sc_host = sc_host
        self.sc_port = sc_port
        self.sc_client = udp_client.SimpleUDPClient(sc_host, sc_port)
        
        # Directories
        self.stems_dir = Path(stems_dir)
        self.structures_dir = Path(structures_dir)
        
        # Mixing state
        self.master_bpm = 120.0  # Starting BPM
        self.target_key = "C"    # Starting key
        self.current_mix = {
            'vocals': None,
            'bass': None,
            'piano': None,
            'drums': None
        }
        
        # Song database
        self.songs = []
        self.song_structures = {}
        
        # Buffer management
        self.next_buffer_id = 2000  # Start higher to avoid conflicts
        self.active_buffers = {}
        
        # Mixing parameters
        self.bpm_tolerance = 0.15  # ±15% BPM range
        self.harmony_threshold = 0.7  # Minimum harmony score
        
        print(f"🎵🎯 CAMELOT WHEEL AUTOMIXER INITIALIZING 🎯🎵")
        print(f"🎼 Starting BPM: {self.master_bpm}")
        print(f"🎹 Starting Key: {self.target_key}")
        print(f"🔄 BPM Tolerance: ±{self.bpm_tolerance*100:.0f}%")
        print(f"🎯 Harmony Threshold: {self.harmony_threshold}")
        
        self._load_songs()
        
    def _load_songs(self):
        """Load song metadata and structure information"""
        print("📚 Loading song database...")
        
        # Load song structures
        if self.structures_dir.exists():
            for json_file in self.structures_dir.glob("*.json"):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    song_id = json_file.stem
                    self.song_structures[song_id] = {
                        'bpm': data.get('bpm', 120),
                        'key': data.get('key', 'C'),  # If available in JSON
                        'segments': data.get('segments', [])
                    }
                except Exception as e:
                    print(f"⚠️  Could not load structure {json_file.name}: {e}")
        
        # Load song stems and estimate keys
        if self.stems_dir.exists():
            for song_dir in self.stems_dir.iterdir():
                if song_dir.is_dir():
                    song_data = self._analyze_song(song_dir)
                    if song_data:
                        self.songs.append(song_data)
        
        print(f"✅ Loaded {len(self.songs)} songs with harmonic analysis")
    
    def _analyze_song(self, song_dir: Path) -> Optional[Dict]:
        """Analyze individual song and estimate key if not provided"""
        song_id = song_dir.name
        
        # Check for available stems
        stems = {}
        for stem_type in ['vocals', 'bass', 'piano', 'drums', 'other']:
            stem_file = song_dir / f"{stem_type}.wav"
            if stem_file.exists():
                stems[stem_type] = stem_file
        
        if len(stems) < 2:  # Need at least 2 stems
            return None
        
        # Get structure data if available
        structure = self.song_structures.get(song_id, {})
        bpm = structure.get('bpm', 120)
        
        # Estimate key if not provided
        estimated_key = self._estimate_key(song_id, bpm)
        key = structure.get('key', estimated_key)
        
        song_data = {
            'id': song_id,
            'name': song_dir.name.replace('_', ' ').title(),
            'stems': stems,
            'bpm': bpm,
            'key': key,
            'camelot_code': CamelotWheel.get_camelot_code(key),
            'segments': structure.get('segments', [])
        }
        
        camelot_display = song_data['camelot_code'] or "Unknown"
        print(f"🎵 {song_data['name'][:30]:30s} | {bpm:3.0f} BPM | {key:4s} | {camelot_display}")
        
        return song_data
    
    def _estimate_key(self, song_id: str, bpm: float) -> str:
        """Estimate musical key based on song characteristics"""
        # Simple heuristic key estimation based on BPM and song patterns
        # In a real system, this would use audio analysis
        
        # Map BPM ranges to common Eurovision keys
        if bpm < 80:
            return random.choice(['Am', 'Em', 'Dm'])  # Slower ballads often minor
        elif bpm < 100:
            return random.choice(['C', 'G', 'F', 'Am'])
        elif bpm < 130:
            return random.choice(['C', 'G', 'D', 'A', 'Em', 'Bm'])
        else:
            return random.choice(['G', 'D', 'A', 'E', 'B'])  # Faster songs often major
    
    def _calculate_bpm_compatibility(self, source_bpm: float, target_bpm: float) -> Tuple[bool, float]:
        """Calculate if BPMs are compatible and return stretch ratio"""
        ratio = target_bpm / source_bpm
        
        # Check if within tolerance without stretching
        if abs(ratio - 1.0) <= self.bpm_tolerance:
            return True, ratio
        
        # Check if half/double speed works
        half_ratio = target_bpm / (source_bpm * 2)
        if abs(half_ratio - 1.0) <= self.bpm_tolerance:
            return True, half_ratio
        
        double_ratio = target_bpm / (source_bpm / 2)
        if abs(double_ratio - 1.0) <= self.bpm_tolerance:
            return True, double_ratio
        
        return False, ratio
    
    def _find_compatible_stems(self, stem_type: str) -> List[Dict]:
        """Find stems compatible with current key and BPM"""
        compatible = []
        
        for song in self.songs:
            if stem_type not in song['stems']:
                continue
            
            # Drums are harmonically neutral
            if stem_type == 'drums':
                harmony_score = 1.0
            else:
                harmony_score = CamelotWheel.calculate_harmony_score(
                    self.target_key, song['key']
                )
            
            # Check BPM compatibility
            bpm_compatible, stretch_ratio = self._calculate_bpm_compatibility(
                song['bpm'], self.master_bpm
            )
            
            if harmony_score >= self.harmony_threshold and bpm_compatible:
                # Calculate overall compatibility score
                bpm_score = 1.0 - abs(stretch_ratio - 1.0)  # Closer to 1.0 is better
                overall_score = (harmony_score * 0.7) + (bpm_score * 0.3)
                
                compatible.append({
                    'song': song,
                    'harmony_score': harmony_score,
                    'bmp_score': bpm_score,
                    'stretch_ratio': stretch_ratio,
                    'overall_score': overall_score
                })
        
        # Sort by overall compatibility score
        compatible.sort(key=lambda x: x['overall_score'], reverse=True)
        return compatible
    
    def _load_and_play_stem(self, song: Dict, stem_type: str, stretch_ratio: float, volume: float = 0.8):
        """Load and play a stem with proper pitch and time adjustments"""
        stem_file = song['stems'][stem_type]
        buffer_id = self.next_buffer_id
        self.next_buffer_id += 1
        
        stem_name = f"{song['name']}_{stem_type}"
        
        try:
            # Load buffer
            self.sc_client.send_message("/load_buffer", [
                buffer_id,
                str(stem_file.absolute()),
                stem_name
            ])
            
            # Wait for load
            time.sleep(1.5 if buffer_id == 2000 else 1.0)
            
            # Calculate pitch shift for harmonic alignment
            pitch_shift = self._calculate_pitch_shift(song['key'], self.target_key)
            
            # Apply both time stretching and pitch shifting
            final_rate = stretch_ratio * pitch_shift
            
            # Play stem
            self.sc_client.send_message("/play_stem", [
                buffer_id,
                final_rate,
                volume,
                1,  # loop
                0.0  # start pos
            ])
            
            # Store buffer info
            self.active_buffers[stem_type] = {
                'buffer_id': buffer_id,
                'song': song,
                'stretch_ratio': stretch_ratio,
                'pitch_shift': pitch_shift,
                'final_rate': final_rate
            }
            
            harmony_score = CamelotWheel.calculate_harmony_score(song['key'], self.target_key)
            
            print(f"▶️  {stem_type:6s}: {song['name'][:25]:25s} | "
                  f"{song['key']:4s}→{self.target_key:4s} | "
                  f"H:{harmony_score:.2f} | "
                  f"R:{final_rate:.3f} | "
                  f"🎵{buffer_id}")
            
            return buffer_id
            
        except Exception as e:
            print(f"❌ Error loading {stem_name}: {e}")
            return None
    
    def _calculate_pitch_shift(self, source_key: str, target_key: str) -> float:
        """Calculate pitch shift ratio for harmonic alignment"""
        # For now, return 1.0 (no pitch shift)
        # In a full implementation, this would calculate semitone differences
        # and convert to playback rate adjustments
        
        # Example calculation (simplified):
        # semitone_diff = calculate_semitone_difference(source_key, target_key)
        # return 2.0 ** (semitone_diff / 12.0)
        
        return 1.0
    
    def _stop_stem(self, stem_type: str):
        """Stop and cleanup a specific stem"""
        if stem_type in self.active_buffers:
            buffer_info = self.active_buffers[stem_type]
            buffer_id = buffer_info['buffer_id']
            
            try:
                self.sc_client.send_message("/stop_stem", [buffer_id])
                print(f"⏹️  Stopped {stem_type} (buffer {buffer_id})")
            except Exception as e:
                print(f"❌ Error stopping {stem_type}: {e}")
            
            del self.active_buffers[stem_type]
    
    def create_harmonic_mix(self, target_key: str = None, master_bpm: float = None):
        """Create a new harmonic mix using Camelot Wheel theory"""
        if target_key:
            self.target_key = target_key
        if master_bpm:
            self.master_bpm = master_bpm
        
        print(f"\n🎯 CREATING HARMONIC MIX")
        print(f"🎹 Target Key: {self.target_key} ({CamelotWheel.get_camelot_code(self.target_key)})")
        print(f"🎵 Master BPM: {self.master_bpm}")
        print("=" * 60)
        
        # Stop all current stems
        for stem_type in list(self.active_buffers.keys()):
            self._stop_stem(stem_type)
        
        # Select new stems for each type
        stem_types = ['vocals', 'bass', 'piano', 'drums']
        
        for stem_type in stem_types:
            compatible_stems = self._find_compatible_stems(stem_type)
            
            if compatible_stems:
                # Select best compatible stem
                best_stem = compatible_stems[0]
                song = best_stem['song']
                stretch_ratio = best_stem['stretch_ratio']
                
                # Set volume based on stem type
                volume = {
                    'vocals': 0.9,
                    'bass': 0.8,
                    'piano': 0.6,
                    'drums': 0.7
                }.get(stem_type, 0.8)
                
                self._load_and_play_stem(song, stem_type, stretch_ratio, volume)
            else:
                print(f"❌ No compatible {stem_type} stems found")
        
        # Set crossfade for balanced mix
        try:
            self.sc_client.send_message("/crossfade_levels", [0.8, 0.8])
        except:
            pass
        
        print("=" * 60)
        print(f"✅ Harmonic mix created with {len(self.active_buffers)} stems")
    
    def evolve_mix(self):
        """Evolve the current mix by changing one stem to a compatible one"""
        if not self.active_buffers:
            print("❌ No active mix to evolve")
            return
        
        # Choose random stem type to evolve
        stem_type = random.choice(list(self.active_buffers.keys()))
        
        print(f"\n🔄 EVOLVING MIX: Changing {stem_type}...")
        
        # Find alternative compatible stems
        compatible_stems = self._find_compatible_stems(stem_type)
        
        # Filter out currently playing song
        current_song_id = self.active_buffers[stem_type]['song']['id']
        compatible_stems = [s for s in compatible_stems if s['song']['id'] != current_song_id]
        
        if compatible_stems:
            # Stop current stem
            self._stop_stem(stem_type)
            
            # Play new stem
            best_stem = compatible_stems[0]
            song = best_stem['song']
            stretch_ratio = best_stem['stretch_ratio']
            
            volume = {
                'vocals': 0.9,
                'bass': 0.8,
                'piano': 0.6,
                'drums': 0.7
            }.get(stem_type, 0.8)
            
            self._load_and_play_stem(song, stem_type, stretch_ratio, volume)
            print("✅ Mix evolved successfully")
        else:
            print(f"❌ No alternative {stem_type} stems available")
    
    def change_key(self, new_key: str):
        """Transition to a new key maintaining harmonic flow"""
        old_key = self.target_key
        
        # Check if new key is harmonically related to current key
        compatible_keys = CamelotWheel.get_compatible_keys(old_key)
        harmony_score = CamelotWheel.calculate_harmony_score(old_key, new_key)
        
        print(f"\n🎹 KEY TRANSITION: {old_key} → {new_key}")
        print(f"🎯 Harmony Score: {harmony_score:.2f}")
        
        if harmony_score >= 0.7:
            print("✅ Smooth harmonic transition")
        elif new_key in compatible_keys:
            print("⚠️  Compatible but challenging transition")
        else:
            print("❌ Dissonant transition - consider intermediate key")
        
        self.target_key = new_key
        
        # Recreate mix with new key
        self.create_harmonic_mix()
    
    def adjust_bpm(self, new_bpm: float):
        """Adjust master BPM and update all playing stems"""
        old_bpm = self.master_bpm
        self.master_bpm = new_bpm
        
        print(f"\n🎵 BPM TRANSITION: {old_bpm:.0f} → {new_bpm:.0f}")
        
        # Update all active stems with new rates
        for stem_type, buffer_info in self.active_buffers.items():
            song = buffer_info['song']
            buffer_id = buffer_info['buffer_id']
            
            # Recalculate stretch ratio
            _, new_stretch_ratio = self._calculate_bpm_compatibility(song['bpm'], new_bpm)
            pitch_shift = buffer_info['pitch_shift']
            new_final_rate = new_stretch_ratio * pitch_shift
            
            try:
                # Update playback rate
                self.sc_client.send_message("/play_stem", [
                    buffer_id,
                    new_final_rate,
                    0.8,  # volume
                    1,    # loop
                    0.0   # start pos
                ])
                
                buffer_info['stretch_ratio'] = new_stretch_ratio
                buffer_info['final_rate'] = new_final_rate
                
                print(f"🔄 Updated {stem_type}: rate {new_final_rate:.3f}")
                
            except Exception as e:
                print(f"❌ Error updating {stem_type}: {e}")
    
    def show_harmonic_analysis(self):
        """Display current harmonic analysis"""
        print(f"\n🎼 HARMONIC ANALYSIS")
        print("=" * 60)
        print(f"Current Key: {self.target_key} ({CamelotWheel.get_camelot_code(self.target_key)})")
        print(f"Master BPM: {self.master_bpm}")
        
        compatible_keys = CamelotWheel.get_compatible_keys(self.target_key)
        print(f"Compatible Keys: {', '.join(compatible_keys)}")
        
        print(f"\nActive Stems ({len(self.active_buffers)}):")
        for stem_type, buffer_info in self.active_buffers.items():
            song = buffer_info['song']
            harmony = CamelotWheel.calculate_harmony_score(song['key'], self.target_key)
            print(f"  {stem_type:8s}: {song['name'][:20]:20s} | "
                  f"{song['key']:4s} | H:{harmony:.2f} | R:{buffer_info['final_rate']:.3f}")
        
        print("=" * 60)
    
    def interactive_mode(self):
        """Interactive Camelot Wheel automixer"""
        print(f"\n🎯 CAMELOT WHEEL AUTOMIXER - INTERACTIVE MODE")
        print("Commands:")
        print("  mix [key] [bpm]     - Create harmonic mix (e.g., 'mix Am 128')")
        print("  evolve              - Evolve current mix")
        print("  key <key>           - Change key (e.g., 'key G')")
        print("  bpm <bpm>           - Change BPM (e.g., 'bpm 130')")
        print("  analysis            - Show harmonic analysis")
        print("  random              - Random harmonic mix")
        print("  wheel               - Show Camelot Wheel")
        print("  quit                - Exit")
        print()
        
        # Create initial mix
        self.create_harmonic_mix()
        
        while True:
            try:
                cmd = input("🎯🎵 > ").strip().lower()
                if not cmd:
                    continue
                
                parts = cmd.split()
                command = parts[0]
                
                if command == "quit":
                    break
                elif command == "mix":
                    key = parts[1] if len(parts) > 1 else self.target_key
                    bpm = float(parts[2]) if len(parts) > 2 else self.master_bpm
                    self.create_harmonic_mix(key, bpm)
                elif command == "evolve":
                    self.evolve_mix()
                elif command == "key" and len(parts) == 2:
                    self.change_key(parts[1])
                elif command == "bpm" and len(parts) == 2:
                    self.adjust_bpm(float(parts[1]))
                elif command == "analysis":
                    self.show_harmonic_analysis()
                elif command == "random":
                    random_key = random.choice(['C', 'G', 'D', 'A', 'E', 'F', 'Am', 'Em', 'Bm', 'Dm'])
                    random_bpm = random.uniform(100, 140)
                    self.create_harmonic_mix(random_key, random_bpm)
                elif command == "wheel":
                    self._show_camelot_wheel()
                else:
                    print("❌ Unknown command")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Error: {e}")
        
        # Cleanup
        print("\n🛑 Stopping Camelot Automixer...")
        for stem_type in list(self.active_buffers.keys()):
            self._stop_stem(stem_type)
        
        try:
            self.sc_client.send_message("/mixer_cleanup", [])
        except:
            pass
        
        print("👋 Camelot Automixer stopped!")
    
    def _show_camelot_wheel(self):
        """Display the Camelot Wheel"""
        print("\n🎯 CAMELOT WHEEL")
        print("=" * 40)
        print("Position | Major | Minor")
        print("-" * 40)
        for number, (major, minor) in CamelotWheel.WHEEL.items():
            marker = " ◄" if self.target_key in [major, minor] else ""
            print(f"   {number:2d}    |  {major:4s} |  {minor:4s}{marker}")
        print("=" * 40)
        print("Mixing Rules:")
        print("• Same number, different letter (relative major/minor)")
        print("• Adjacent numbers, same letter (±1 position)")
        print("• Perfect fifth (±7 positions)")
        print()

def main():
    """Main entry point"""
    print("🎯🎵 Starting Camelot Wheel Automixer...")
    
    try:
        automixer = CamelotAutomixer()
        automixer.interactive_mode()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()