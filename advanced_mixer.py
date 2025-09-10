#!/usr/bin/env python3
"""
Advanced Real-time Music Mixing Engine with Key Detection and Enhanced Features
"""

import json
import os
import random
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import numpy as np

@dataclass 
class Song:
    name: str
    bpm: int
    beats: List[float]
    downbeats: List[float] 
    segments: List[Dict[str, Any]]
    stems_path: str
    key: Optional[str] = None  # We'll estimate this
    
    @property
    def stem_files(self) -> Dict[str, str]:
        stems_dir = Path(self.stems_path)
        stems = {}
        for stem_file in stems_dir.glob("*.wav"):
            stem_type = stem_file.stem
            stems[stem_type] = str(stem_file)
        return stems
    
    def get_segments_by_type(self, segment_type: str) -> List[Dict[str, Any]]:
        return [seg for seg in self.segments if seg['label'] == segment_type]
    
    @property 
    def available_sections(self) -> List[str]:
        return list(set(seg['label'] for seg in self.segments))

class KeyCompatibility:
    CAMELOT_WHEEL = {
        'C': '8B', 'Am': '8A', 'G': '9B', 'Em': '9A', 'D': '10B', 'Bm': '10A',
        'A': '11B', 'F#m': '11A', 'E': '12B', 'C#m': '12A', 'B': '1B', 'G#m': '1A',
        'F#': '2B', 'D#m': '2A', 'Db': '3B', 'Bbm': '3A', 'Ab': '4B', 'Fm': '4A',
        'Eb': '5B', 'Cm': '5A', 'Bb': '6B', 'Gm': '6A', 'F': '7B', 'Dm': '7A'
    }
    
    CAMELOT_TO_KEY = {v: k for k, v in CAMELOT_WHEEL.items()}
    
    # Simple key estimation based on BPM and song characteristics
    KEY_ESTIMATION = {
        67: 'Am',   # Wasted Love - emotional ballad
        86: 'Dm',   # Poison Cake - dark minor
        95: 'Em',   # Zjerm - folk-ish
        115: 'G',   # Run With U - upbeat major
        120: 'F',   # Espresso Macchiato - smooth
        125: 'C',   # Kiss Kiss Goodbye - pop major
        133: 'Am',  # SURVIVOR - dramatic minor
        140: 'D',   # Hallucination - electronic major
        143: 'A',   # Shh - bright major
        146: 'E',   # Strobe Lights - high energy
        154: 'B'    # Milkshake Man - very fast major
    }
    
    @classmethod
    def estimate_key(cls, bpm: int) -> str:
        """Estimate key based on BPM and style"""
        return cls.KEY_ESTIMATION.get(bpm, 'C')
    
    @classmethod
    def get_compatible_keys(cls, key: str) -> List[str]:
        if key not in cls.CAMELOT_WHEEL:
            return [key]
            
        camelot = cls.CAMELOT_WHEEL[key]
        number = int(camelot[:-1])
        letter = camelot[-1]
        
        compatible_camelot = []
        compatible_camelot.append(camelot)
        
        # Adjacent numbers (±1)
        for adj in [-1, 1]:
            adj_num = (number + adj - 1) % 12 + 1
            compatible_camelot.append(f"{adj_num}{letter}")
        
        # Relative major/minor
        opposite_letter = 'A' if letter == 'B' else 'B'
        compatible_camelot.append(f"{number}{opposite_letter}")
        
        # Perfect 5th (±7 positions)
        fifth_up = (number + 6) % 12 + 1
        fifth_down = (number - 8) % 12 + 1
        compatible_camelot.extend([f"{fifth_up}{letter}", f"{fifth_down}{letter}"])
        
        compatible_keys = []
        for camelot_key in compatible_camelot:
            if camelot_key in cls.CAMELOT_TO_KEY:
                compatible_keys.append(cls.CAMELOT_TO_KEY[camelot_key])
        
        return list(set(compatible_keys))

class BPMTolerance:
    @staticmethod
    def is_compatible(bpm1: int, bpm2: int, tolerance_percent: float = 8.0) -> bool:
        # Increased tolerance for more mixing possibilities
        tolerance = bpm1 * (tolerance_percent / 100)
        return abs(bpm1 - bpm2) <= tolerance
    
    @staticmethod
    def calculate_pitch_shift(source_bpm: int, target_bpm: int) -> float:
        """Calculate pitch shift ratio needed"""
        return target_bpm / source_bpm
    
    @staticmethod
    def get_tempo_variants(bpm: int) -> List[int]:
        """Get tempo variants (half-time, double-time, etc.)"""
        return [bpm // 2, bpm, bpm * 2]

class AdvancedMusicMixer:
    def __init__(self, stems_dir: str, structures_dir: str):
        self.stems_dir = stems_dir
        self.structures_dir = structures_dir
        self.songs: Dict[str, Song] = {}
        self.load_songs()
        self.estimate_keys()
    
    def load_songs(self):
        structures_path = Path(self.structures_dir)
        stems_path = Path(self.stems_dir)
        
        for json_file in structures_path.glob("*.json"):
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            song_name = json_file.stem
            song_stems_dir = stems_path / song_name
            
            if song_stems_dir.exists():
                song = Song(
                    name=song_name,
                    bpm=data['bpm'],
                    beats=data['beats'],
                    downbeats=data['downbeats'],
                    segments=data['segments'],
                    stems_path=str(song_stems_dir)
                )
                self.songs[song_name] = song
                print(f"Loaded: {song_name} (BPM: {song.bpm})")
    
    def estimate_keys(self):
        """Estimate keys for all songs"""
        for song in self.songs.values():
            song.key = KeyCompatibility.estimate_key(song.bpm)
            print(f"Estimated key for {song.name}: {song.key}")
    
    def create_intelligent_remix(self, theme: str = "energetic") -> Dict[str, Any]:
        """Create an intelligent remix based on theme"""
        
        themes = {
            "energetic": {
                "preferred_bpm": 140,
                "structure": ["intro", "verse", "chorus", "verse", "bridge", "chorus", "chorus", "outro"],
                "stem_strategy": "high_energy"
            },
            "chill": {
                "preferred_bpm": 95,
                "structure": ["intro", "verse", "chorus", "verse", "solo", "chorus", "outro"],
                "stem_strategy": "smooth"
            },
            "dramatic": {
                "preferred_bpm": 125,
                "structure": ["verse", "verse", "chorus", "bridge", "bridge", "chorus", "chorus"],
                "stem_strategy": "emotional"
            }
        }
        
        if theme not in themes:
            theme = "energetic"
            
        theme_config = themes[theme]
        
        # Find songs closest to preferred BPM
        preferred_bpm = theme_config["preferred_bpm"]
        songs_by_distance = sorted(
            self.songs.values(), 
            key=lambda s: abs(s.bpm - preferred_bpm)
        )
        
        reference_song = songs_by_distance[0]
        print(f"Creating {theme} remix based on: {reference_song.name} (BPM: {reference_song.bpm}, Key: {reference_song.key})")
        
        # Find compatible songs (increased tolerance)
        compatible_songs = []
        reference_key_compatible = KeyCompatibility.get_compatible_keys(reference_song.key)
        
        for song in self.songs.values():
            if song.name == reference_song.name:
                continue
                
            # Check BPM compatibility with higher tolerance
            if BPMTolerance.is_compatible(reference_song.bpm, song.bpm, tolerance_percent=15.0):
                if song.key in reference_key_compatible:
                    compatible_songs.append(song)
                    print(f"  Compatible: {song.name} (BPM: {song.bpm}, Key: {song.key})")
        
        structure = theme_config["structure"]
        
        remix_plan = {
            "theme": theme,
            "base_song": reference_song.name,
            "base_bpm": reference_song.bpm,
            "base_key": reference_song.key,
            "structure": structure,
            "sections": {},
            "compatible_songs": [s.name for s in compatible_songs]
        }
        
        # Intelligent stem selection based on theme
        for i, section_type in enumerate(structure):
            section_key = f"{i:02d}_{section_type}"
            stems = self.select_intelligent_stems(
                section_type, reference_song, compatible_songs, theme_config["stem_strategy"]
            )
            
            remix_plan["sections"][section_key] = {
                "type": section_type,
                "stems": {}
            }
            
            for stem_type, (song, file_path) in stems.items():
                pitch_shift = BPMTolerance.calculate_pitch_shift(song.bpm, reference_song.bpm)
                remix_plan["sections"][section_key]["stems"][stem_type] = {
                    "song": song.name,
                    "file": file_path,
                    "bpm": song.bpm,
                    "key": song.key,
                    "pitch_shift": pitch_shift,
                    "needs_timestretch": abs(pitch_shift - 1.0) > 0.05
                }
        
        return remix_plan
    
    def select_intelligent_stems(self, section_type: str, reference_song: Song, 
                               compatible_songs: List[Song], strategy: str) -> Dict[str, Tuple[Song, str]]:
        """Intelligent stem selection based on strategy"""
        selected_stems = {}
        available_stems = ["bass", "drums", "other", "piano", "vocals"]
        songs_pool = [reference_song] + compatible_songs
        
        # Strategy-based selection
        if strategy == "high_energy":
            # Prefer higher BPM songs for drums, keep vocals consistent
            stem_preferences = {
                "drums": lambda songs: sorted(songs, key=lambda s: s.bpm, reverse=True),
                "bass": lambda songs: sorted(songs, key=lambda s: s.bpm, reverse=True),
                "vocals": lambda songs: [reference_song] if reference_song in songs else songs,
                "piano": lambda songs: songs,
                "other": lambda songs: sorted(songs, key=lambda s: s.bpm, reverse=True)
            }
        elif strategy == "smooth":
            # Prefer lower BPM, more consistent selection
            stem_preferences = {
                "drums": lambda songs: sorted(songs, key=lambda s: s.bpm),
                "bass": lambda songs: sorted(songs, key=lambda s: s.bpm),
                "vocals": lambda songs: songs,
                "piano": lambda songs: sorted(songs, key=lambda s: s.bpm),
                "other": lambda songs: songs
            }
        else:  # emotional
            # Mix high and low, create dynamic contrasts
            stem_preferences = {
                "drums": lambda songs: songs,
                "bass": lambda songs: sorted(songs, key=lambda s: s.bpm),
                "vocals": lambda songs: sorted(songs, key=lambda s: abs(s.bpm - 120)),
                "piano": lambda songs: songs,
                "other": lambda songs: songs
            }
        
        for stem_type in available_stems:
            candidates = []
            for song in songs_pool:
                if stem_type in song.stem_files:
                    # Check if song has required section or can be adapted
                    if (song.get_segments_by_type(section_type) or 
                        section_type in ["intro", "outro", "bridge"]):  # These can be adapted
                        candidates.append(song)
            
            if candidates and stem_type in stem_preferences:
                preferred_candidates = stem_preferences[stem_type](candidates)
                if preferred_candidates:
                    chosen_song = preferred_candidates[0]
                    selected_stems[stem_type] = (chosen_song, chosen_song.stem_files[stem_type])
        
        return selected_stems
    
    def print_advanced_remix_plan(self, remix_plan: Dict[str, Any]):
        """Print detailed remix plan with technical details"""
        print(f"\n🎵 ADVANCED REMIX PLAN - {remix_plan['theme'].upper()} THEME 🎵")
        print(f"Base Song: {remix_plan['base_song']}")
        print(f"Base BPM: {remix_plan['base_bpm']} | Base Key: {remix_plan['base_key']}")
        print(f"Compatible Songs: {', '.join(remix_plan['compatible_songs'])}")
        print(f"Structure: {' -> '.join(remix_plan['structure'])}")
        print("\nSection Details:")
        print("-" * 100)
        
        for section_key, section_data in remix_plan["sections"].items():
            section_type = section_data["type"]
            print(f"\n{section_key.upper()}: {section_type.upper()}")
            
            for stem_type, stem_data in section_data["stems"].items():
                song_name = stem_data["song"].split("(")[0].strip()
                bpm = stem_data["bpm"]
                key = stem_data["key"]
                pitch_shift = stem_data["pitch_shift"]
                needs_timestretch = stem_data["needs_timestretch"]
                
                timestretch_info = " [TIMESTRETCH]" if needs_timestretch else ""
                print(f"  {stem_type:8} -> {song_name:20} (BPM: {bpm:3d}, Key: {key:3s}, Shift: {pitch_shift:.2f}){timestretch_info}")
    
    def analyze_mixing_possibilities(self):
        """Analyze and display mixing possibilities"""
        print(f"\n🔍 MIXING ANALYSIS")
        print("=" * 60)
        
        # BPM clusters
        bpm_clusters = {}
        for song in self.songs.values():
            cluster = (song.bpm // 20) * 20  # Group by 20 BPM ranges
            if cluster not in bpm_clusters:
                bpm_clusters[cluster] = []
            bpm_clusters[cluster].append(song)
        
        print("\n📊 BPM CLUSTERS (±15% mixing tolerance):")
        for cluster_bpm in sorted(bpm_clusters.keys()):
            songs_in_cluster = bpm_clusters[cluster_bpm]
            if len(songs_in_cluster) > 1:
                print(f"\n{cluster_bpm}-{cluster_bpm+19} BPM Range:")
                for song in songs_in_cluster:
                    print(f"  {song.bpm:3d} BPM - {song.name} (Key: {song.key})")
        
        # Key compatibility analysis
        print(f"\n🎼 KEY COMPATIBILITY ANALYSIS:")
        keys_used = set(song.key for song in self.songs.values())
        for key in sorted(keys_used):
            compatible_keys = KeyCompatibility.get_compatible_keys(key)
            songs_with_key = [s for s in self.songs.values() if s.key == key]
            compatible_songs = [s for s in self.songs.values() if s.key in compatible_keys and s.key != key]
            
            print(f"\nKey {key}:")
            print(f"  Songs: {', '.join([s.name.split('(')[0].strip() for s in songs_with_key])}")
            if compatible_songs:
                compatible_names = [f"{s.name.split('(')[0].strip()} ({s.key})" for s in compatible_songs]
                print(f"  Compatible: {', '.join(compatible_names)}")

def main():
    """Enhanced main function with multiple remix examples"""
    mixer = AdvancedMusicMixer("stems", "song-structures")
    
    # Analysis
    mixer.analyze_mixing_possibilities()
    
    print("\n" + "="*100)
    print("CREATING THEMED REMIXES")
    print("="*100)
    
    themes = ["energetic", "chill", "dramatic"]
    
    for theme in themes:
        print(f"\n{'='*50}")
        print(f"THEME: {theme.upper()}")
        print(f"{'='*50}")
        
        remix = mixer.create_intelligent_remix(theme)
        mixer.print_advanced_remix_plan(remix)
        
        print(f"\n💡 Mixing Tips for {theme.upper()} theme:")
        if theme == "energetic":
            print("  - Use high-BPM drums and bass for drive")
            print("  - Layer vocals from different songs for excitement") 
            print("  - Apply compression and EQ boost to enhance energy")
        elif theme == "chill":
            print("  - Keep consistent, lower BPM throughout")
            print("  - Use reverb and delay effects on vocals")
            print("  - Smooth transitions between sections")
        else:  # dramatic
            print("  - Create dynamic contrasts between sections")
            print("  - Use minor key stems for emotional impact")
            print("  - Build intensity toward climax sections")

if __name__ == "__main__":
    main()