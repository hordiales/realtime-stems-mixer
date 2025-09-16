#!/usr/bin/env python3
"""
TSP AutoDJ - Traveling Salesman Problem approach to song ordering
Finds optimal path through all songs considering BPM and key compatibility (Camelot wheel)
"""

import os
import sys
import json
import random
import itertools
import numpy as np
import librosa
import soundfile as sf
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from threading import Thread, Event
import time
import pyaudio

@dataclass
class SongMetadata:
    """Song metadata including BPM and key info"""
    path: str
    name: str
    bpm: float
    key: str  # Camelot notation (e.g., "8A", "12B")
    energy: float
    duration: float

class CamelotWheel:
    """Camelot wheel for harmonic mixing distance calculations"""
    
    # Camelot wheel mapping
    WHEEL_POSITIONS = {
        '1A': 0, '1B': 1, '2A': 2, '2B': 3, '3A': 4, '3B': 5,
        '4A': 6, '4B': 7, '5A': 8, '5B': 9, '6A': 10, '6B': 11,
        '7A': 12, '7B': 13, '8A': 14, '8B': 15, '9A': 16, '9B': 17,
        '10A': 18, '10B': 19, '11A': 20, '11B': 21, '12A': 22, '12B': 23
    }
    
    # Reverse mapping
    POSITION_TO_KEY = {v: k for k, v in WHEEL_POSITIONS.items()}
    
    @classmethod
    def key_distance(cls, key1: str, key2: str) -> float:
        """
        Calculate harmonic distance between two keys on Camelot wheel
        Returns normalized distance (0.0 = perfect match, 1.0 = tritone)
        """
        if key1 == key2:
            return 0.0
            
        # Handle invalid keys
        if key1 not in cls.WHEEL_POSITIONS or key2 not in cls.WHEEL_POSITIONS:
            return 1.0  # Maximum distance for unknown keys
            
        pos1 = cls.WHEEL_POSITIONS[key1]
        pos2 = cls.WHEEL_POSITIONS[key2]
        
        # Calculate circular distance (A/B sides are adjacent)
        # Convert to circle of fifths positions
        circle_pos1 = pos1 // 2
        circle_pos2 = pos2 // 2
        
        # Circular distance on circle of fifths (12 positions)
        circle_dist = min(abs(circle_pos1 - circle_pos2), 
                         12 - abs(circle_pos1 - circle_pos2))
        
        # A/B side penalty (minor vs major)
        side_penalty = 0.0
        if (pos1 % 2) != (pos2 % 2):  # Different sides (A vs B)
            side_penalty = 0.2
            
        # Normalize: 0 = same key, 6 = tritone (maximum harmonic distance)
        normalized_dist = (circle_dist / 6.0) + side_penalty
        
        return min(normalized_dist, 1.0)
    
    @classmethod
    def get_compatible_keys(cls, key: str, max_distance: float = 0.3) -> List[str]:
        """Get list of harmonically compatible keys within distance threshold"""
        compatible = []
        for other_key in cls.WHEEL_POSITIONS.keys():
            if cls.key_distance(key, other_key) <= max_distance:
                compatible.append(other_key)
        return compatible
    
    @classmethod
    def estimate_key_from_chroma(cls, chroma_features: np.ndarray) -> str:
        """Estimate Camelot key from chromagram features"""
        # Simplified key detection using template matching
        # This is a basic implementation - real key detection is more complex
        
        # Major and minor key templates (circle of fifths order)
        major_template = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
        minor_template = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
        
        # Average chroma across time
        avg_chroma = np.mean(chroma_features, axis=1)
        
        best_correlation = -1
        best_key = "1A"
        
        # Try all 24 keys
        for shift in range(12):
            # Major key correlation
            shifted_chroma_major = np.roll(avg_chroma, shift)
            corr_major = np.corrcoef(shifted_chroma_major, major_template)[0, 1]
            if corr_major > best_correlation:
                best_correlation = corr_major
                best_key = f"{shift + 1}B"  # Major keys are B side
                
            # Minor key correlation  
            shifted_chroma_minor = np.roll(avg_chroma, shift)
            corr_minor = np.corrcoef(shifted_chroma_minor, minor_template)[0, 1]
            if corr_minor > best_correlation:
                best_correlation = corr_minor
                best_key = f"{shift + 1}A"  # Minor keys are A side
                
        return best_key

class BPMDistance:
    """BPM distance calculations for harmonic mixing"""
    
    @staticmethod
    def bpm_distance(bpm1: float, bpm2: float, harmonic_threshold: float = 0.08) -> float:
        """
        Calculate BPM mixing distance considering harmonic relationships
        Returns normalized distance (0.0 = perfect, 1.0 = unmixable)
        """
        if bpm1 == 0 or bpm2 == 0:
            return 1.0
            
        # Test direct mixing compatibility
        ratio = max(bpm1, bpm2) / min(bpm1, bpm2)
        if ratio - 1.0 <= harmonic_threshold:
            return (ratio - 1.0) / harmonic_threshold
            
        # Test harmonic relationships (2:1, 3:2, 4:3 ratios)
        harmonic_ratios = [2.0, 1.5, 4/3, 3/4, 2/3, 0.5]
        
        best_distance = 1.0
        for target_ratio in harmonic_ratios:
            # Check if BPMs are close to this harmonic ratio
            actual_ratio = bpm1 / bpm2
            ratio_error = abs(actual_ratio - target_ratio) / target_ratio
            
            if ratio_error <= harmonic_threshold:
                distance = ratio_error / harmonic_threshold
                best_distance = min(best_distance, distance)
                
        return best_distance
    
    @staticmethod
    def tempo_adjustment_factor(bpm1: float, bpm2: float) -> float:
        """Calculate tempo adjustment factor needed for mixing"""
        if bpm2 == 0:
            return 1.0
        return bpm1 / bpm2

class SongAnalyzer:
    """Analyzes songs to extract metadata for TSP calculations"""
    
    def __init__(self, stems_dir: str = "stems"):
        self.stems_dir = Path(stems_dir)
        self.cache_file = Path("song_analysis_cache.json")
        self.cache = self._load_cache()
        
    def _load_cache(self) -> Dict:
        """Load analysis cache from disk"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  Cache load error: {e}")
        return {}
    
    def _save_cache(self):
        """Save analysis cache to disk"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            print(f"⚠️  Cache save error: {e}")
    
    def analyze_song(self, song_path: Path) -> Optional[SongMetadata]:
        """Analyze a single song directory and extract metadata"""
        
        song_name = song_path.name
        cache_key = f"{song_name}_{song_path.stat().st_mtime}"
        
        # Check cache first
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            return SongMetadata(**cached)
        
        try:
            # Find main audio file (prefer vocals, then other, then any)
            audio_files = ['vocals.wav', 'other.wav', 'bass.wav', 'drums.wav', 'piano.wav']
            main_audio = None
            
            for filename in audio_files:
                audio_path = song_path / filename
                if audio_path.exists():
                    main_audio = str(audio_path)
                    break
                    
            if not main_audio:
                print(f"⚠️  No audio files found in {song_name}")
                return None
                
            print(f"🎵 Analyzing: {song_name}")
            
            # Load audio
            y, sr = librosa.load(main_audio, duration=60, sr=22050)  # Analyze first 60 seconds
            
            # BPM detection
            tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
            
            # Key detection using chromagram
            chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
            estimated_key = CamelotWheel.estimate_key_from_chroma(chroma)
            
            # Energy calculation
            rms_energy = np.mean(librosa.feature.rms(y=y))
            
            # Duration
            duration = len(y) / sr
            
            metadata = SongMetadata(
                path=str(song_path),
                name=song_name,
                bpm=float(tempo),
                key=estimated_key,
                energy=float(rms_energy),
                duration=duration
            )
            
            # Cache the result
            self.cache[cache_key] = {
                'path': metadata.path,
                'name': metadata.name,
                'bpm': metadata.bpm,
                'key': metadata.key,
                'energy': metadata.energy,
                'duration': metadata.duration
            }
            self._save_cache()
            
            print(f"  BPM: {metadata.bpm:.1f}, Key: {metadata.key}, Energy: {metadata.energy:.3f}")
            
            return metadata
            
        except Exception as e:
            print(f"❌ Error analyzing {song_name}: {e}")
            return None
    
    def analyze_all_songs(self) -> List[SongMetadata]:
        """Analyze all songs in the stems directory"""
        songs = []
        
        if not self.stems_dir.exists():
            print(f"❌ Stems directory not found: {self.stems_dir}")
            return songs
            
        print(f"🔍 Scanning {self.stems_dir} for songs...")
        
        for song_dir in sorted(self.stems_dir.iterdir()):
            if song_dir.is_dir() and not song_dir.name.startswith('.'):
                metadata = self.analyze_song(song_dir)
                if metadata:
                    songs.append(metadata)
                    
        print(f"✅ Analyzed {len(songs)} songs")
        return songs

class TSPSolver:
    """Traveling Salesman Problem solver for song ordering"""
    
    def __init__(self, songs: List[SongMetadata]):
        self.songs = songs
        self.n = len(songs)
        self.distance_matrix = self._build_distance_matrix()
        
    def _build_distance_matrix(self) -> np.ndarray:
        """Build distance matrix between all song pairs"""
        print("🧮 Building distance matrix...")
        
        matrix = np.zeros((self.n, self.n))
        
        for i in range(self.n):
            for j in range(self.n):
                if i == j:
                    matrix[i][j] = 0.0
                else:
                    matrix[i][j] = self._calculate_distance(self.songs[i], self.songs[j])
                    
        return matrix
    
    def _calculate_distance(self, song1: SongMetadata, song2: SongMetadata) -> float:
        """Calculate mixing distance between two songs"""
        
        # Key distance (Camelot wheel)
        key_dist = CamelotWheel.key_distance(song1.key, song2.key)
        
        # BPM distance
        bpm_dist = BPMDistance.bpm_distance(song1.bpm, song2.bpm)
        
        # Energy difference (for smooth energy progression)
        energy_diff = abs(song1.energy - song2.energy)
        energy_dist = min(energy_diff / 0.1, 1.0)  # Normalize energy distance
        
        # Weighted combination (key harmony is most important for mixing)
        total_distance = (
            key_dist * 0.5 +      # 50% key compatibility
            bpm_dist * 0.35 +     # 35% BPM compatibility  
            energy_dist * 0.15    # 15% energy flow
        )
        
        return total_distance
    
    def solve_nearest_neighbor(self, start_index: int = 0) -> List[int]:
        """Solve TSP using nearest neighbor heuristic"""
        print("🚀 Solving TSP with nearest neighbor...")
        
        unvisited = set(range(self.n))
        tour = [start_index]
        unvisited.remove(start_index)
        current = start_index
        
        while unvisited:
            # Find nearest unvisited song
            nearest_distance = float('inf')
            nearest_song = None
            
            for next_song in unvisited:
                distance = self.distance_matrix[current][next_song]
                if distance < nearest_distance:
                    nearest_distance = distance
                    nearest_song = next_song
                    
            tour.append(nearest_song)
            unvisited.remove(nearest_song)
            current = nearest_song
            
        return tour
    
    def improve_2opt(self, tour: List[int], max_iterations: int = 1000) -> List[int]:
        """Improve tour using 2-opt local search"""
        print("🔧 Improving tour with 2-opt...")
        
        best_tour = tour[:]
        best_distance = self._calculate_tour_distance(best_tour)
        
        for iteration in range(max_iterations):
            improved = False
            
            for i in range(1, len(tour) - 2):
                for j in range(i + 1, len(tour)):
                    if j - i == 1: continue  # Skip adjacent edges
                    
                    # Create new tour by reversing segment [i:j]
                    new_tour = tour[:]
                    new_tour[i:j] = reversed(new_tour[i:j])
                    
                    new_distance = self._calculate_tour_distance(new_tour)
                    
                    if new_distance < best_distance:
                        best_tour = new_tour[:]
                        best_distance = new_distance
                        tour = new_tour
                        improved = True
                        break
                        
                if improved:
                    break
                    
            if not improved:
                break
                
        print(f"  Improved tour distance: {best_distance:.3f}")
        return best_tour
    
    def _calculate_tour_distance(self, tour: List[int]) -> float:
        """Calculate total distance of a tour"""
        total = 0.0
        for i in range(len(tour)):
            j = (i + 1) % len(tour)  # Loop back to start
            total += self.distance_matrix[tour[i]][tour[j]]
        return total
    
    def solve(self) -> List[int]:
        """Solve TSP with nearest neighbor + 2-opt improvement"""
        if self.n <= 1:
            return list(range(self.n))
            
        # Try multiple starting points and pick best
        best_tour = None
        best_distance = float('inf')
        
        # Test up to 5 different starting points
        start_points = list(range(min(5, self.n)))
        
        for start in start_points:
            # Nearest neighbor
            tour = self.solve_nearest_neighbor(start)
            
            # 2-opt improvement
            tour = self.improve_2opt(tour)
            
            distance = self._calculate_tour_distance(tour)
            if distance < best_distance:
                best_distance = distance
                best_tour = tour
                
        print(f"✅ Best tour distance: {best_distance:.3f}")
        return best_tour

class TSPAutoDJ:
    """AutoDJ that plays songs in TSP-optimized order"""
    
    def __init__(self, stems_dir: str = "stems"):
        self.analyzer = SongAnalyzer(stems_dir)
        self.songs = []
        self.tour = []
        self.current_index = 0
        self.is_playing = False
        self.stop_event = Event()
        
        # Audio setup
        self.sample_rate = 44100
        self.chunk_size = 1024
        self.audio = pyaudio.PyAudio()
        self.stream = None
        
    def analyze_and_plan_tour(self):
        """Analyze songs and calculate optimal tour"""
        print("🎯 TSP AutoDJ - Finding optimal song tour...")
        
        # Analyze all songs
        self.songs = self.analyzer.analyze_all_songs()
        
        if len(self.songs) < 2:
            print("❌ Need at least 2 songs for TSP")
            return False
            
        # Solve TSP
        solver = TSPSolver(self.songs)
        self.tour = solver.solve()
        
        # Display tour
        print("\n🗺️  OPTIMAL SONG TOUR:")
        print("=" * 60)
        total_distance = 0.0
        
        for i, song_idx in enumerate(self.tour):
            song = self.songs[song_idx]
            print(f"{i+1:2d}. {song.name}")
            print(f"    BPM: {song.bpm:.1f} | Key: {song.key} | Energy: {song.energy:.3f}")
            
            if i > 0:
                prev_idx = self.tour[i-1]
                distance = solver.distance_matrix[prev_idx][song_idx]
                total_distance += distance
                print(f"    Distance from previous: {distance:.3f}")
            print()
            
        print(f"📊 Total tour distance: {total_distance:.3f}")
        print(f"🎵 Average compatibility: {1.0 - (total_distance/len(self.tour)):.1%}")
        
        return True
    
    def play_tour(self):
        """Play the complete TSP tour"""
        if not self.tour:
            print("❌ No tour calculated. Run analyze_and_plan_tour() first.")
            return
            
        print(f"\n🚀 Starting TSP AutoDJ tour ({len(self.tour)} songs)")
        print("Press Ctrl+C to stop")
        
        self.is_playing = True
        self.current_index = 0
        
        try:
            while self.is_playing and self.current_index < len(self.tour):
                song_idx = self.tour[self.current_index]
                song = self.songs[song_idx]
                
                print(f"\n🎵 Now Playing [{self.current_index + 1}/{len(self.tour)}]:")
                print(f"   {song.name}")
                print(f"   BPM: {song.bpm:.1f} | Key: {song.key}")
                
                # Play song (simplified - just show info and wait)
                self._play_song_info(song)
                
                self.current_index += 1
                
                if self.current_index < len(self.tour):
                    next_idx = self.tour[self.current_index]
                    next_song = self.songs[next_idx]
                    print(f"🔄 Next: {next_song.name} (Key: {next_song.key}, BPM: {next_song.bpm:.1f})")
                    
        except KeyboardInterrupt:
            print("\n⏹️  Tour stopped by user")
        finally:
            self.is_playing = False
            
    def _play_song_info(self, song: SongMetadata):
        """Display song info and simulate playback"""
        # In a real implementation, this would load and play the actual audio
        # For now, just simulate with a short wait
        print(f"   Duration: {song.duration:.1f}s")
        
        # Simulate short playback for demo
        for i in range(5):
            if not self.is_playing:
                break
            print(f"   Playing... {i+1}/5")
            time.sleep(1)
    
    def show_tour_stats(self):
        """Display detailed tour statistics"""
        if not self.tour:
            print("❌ No tour calculated")
            return
            
        print("\n📈 TOUR STATISTICS:")
        print("=" * 50)
        
        # BPM analysis
        bpms = [self.songs[i].bpm for i in self.tour]
        print(f"BPM Range: {min(bpms):.1f} - {max(bpms):.1f}")
        print(f"BPM Average: {np.mean(bpms):.1f}")
        
        # Key analysis
        keys = [self.songs[i].key for i in self.tour]
        key_counts = {}
        for key in keys:
            key_counts[key] = key_counts.get(key, 0) + 1
        print(f"Keys used: {len(key_counts)} different keys")
        
        # Energy flow
        energies = [self.songs[i].energy for i in self.tour]
        print(f"Energy Range: {min(energies):.3f} - {max(energies):.3f}")
        print(f"Energy Flow: {energies[0]:.3f} → {energies[-1]:.3f}")

def main():
    """Main TSP AutoDJ interface"""
    print("🎯 TSP AutoDJ - Traveling Salesman Song Optimizer")
    print("=" * 55)
    
    autodj = TSPAutoDJ()
    
    # Analyze and plan
    if not autodj.analyze_and_plan_tour():
        return
        
    # Show statistics
    autodj.show_tour_stats()
    
    # Ask user if they want to play the tour
    try:
        response = input("\n▶️  Play the optimized tour? (y/n): ").strip().lower()
        if response.startswith('y'):
            autodj.play_tour()
        else:
            print("👋 Tour planning complete. Use play_tour() to start playback.")
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

if __name__ == "__main__":
    main()