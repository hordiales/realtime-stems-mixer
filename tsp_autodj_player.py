#!/usr/bin/env python3
"""
TSP AutoDJ Player - Real audio playback with crossfading
Plays the TSP-optimized song tour with smooth transitions
"""

import numpy as np
import librosa
import soundfile as sf
import pyaudio
from threading import Thread, Event, Lock
import time
import queue
from pathlib import Path
from typing import List, Optional, Tuple
from tsp_autodj import TSPAutoDJ, SongMetadata, CamelotWheel, BPMDistance

class AudioMixer:
    """Real-time audio mixer with crossfading capabilities"""
    
    def __init__(self, sample_rate: int = 44100, chunk_size: int = 1024):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.audio = pyaudio.PyAudio()
        self.stream = None
        
        # Audio buffers
        self.current_audio = None
        self.next_audio = None
        self.crossfade_samples = int(sample_rate * 4.0)  # 4 second crossfade
        
        # Playback state
        self.current_position = 0
        self.is_crossfading = False
        self.crossfade_position = 0
        self.master_volume = 0.8
        
        # Threading
        self.audio_lock = Lock()
        self.is_playing = False
        
    def setup_stream(self):
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
        """Audio stream callback for real-time playback"""
        with self.audio_lock:
            if not self.is_playing or self.current_audio is None:
                # Return silence
                return (np.zeros((frame_count, 2), dtype=np.float32).tobytes(), pyaudio.paContinue)
            
            try:
                output = self._generate_audio_chunk(frame_count)
                return (output.tobytes(), pyaudio.paContinue)
            except Exception as e:
                print(f"⚠️  Audio callback error: {e}")
                return (np.zeros((frame_count, 2), dtype=np.float32).tobytes(), pyaudio.paContinue)
    
    def _generate_audio_chunk(self, frame_count: int) -> np.ndarray:
        """Generate audio chunk with crossfading"""
        output = np.zeros((frame_count, 2), dtype=np.float32)
        
        if not self.is_crossfading:
            # Normal playback of current track
            if self.current_position + frame_count < len(self.current_audio):
                output = self.current_audio[self.current_position:self.current_position + frame_count]
                self.current_position += frame_count
            else:
                # End of track - fill with remaining samples and zeros
                remaining = len(self.current_audio) - self.current_position
                if remaining > 0:
                    output[:remaining] = self.current_audio[self.current_position:]
                self.current_position = len(self.current_audio)
                
        else:
            # Crossfade between current and next track
            samples_generated = 0
            
            while samples_generated < frame_count:
                samples_needed = min(frame_count - samples_generated, 
                                   self.crossfade_samples - self.crossfade_position)
                
                if samples_needed <= 0:
                    break
                
                # Calculate crossfade weights
                fade_progress = self.crossfade_position / self.crossfade_samples
                current_weight = 1.0 - fade_progress
                next_weight = fade_progress
                
                # Mix current track
                current_chunk = np.zeros((samples_needed, 2))
                if (self.current_audio is not None and 
                    self.current_position + samples_needed <= len(self.current_audio)):
                    current_chunk = self.current_audio[self.current_position:
                                                     self.current_position + samples_needed]
                
                # Mix next track
                next_chunk = np.zeros((samples_needed, 2))
                if (self.next_audio is not None and 
                    samples_needed <= len(self.next_audio)):
                    next_chunk = self.next_audio[:samples_needed]
                
                # Crossfade
                mixed_chunk = (current_chunk * current_weight + next_chunk * next_weight)
                
                output[samples_generated:samples_generated + samples_needed] = mixed_chunk
                
                self.current_position += samples_needed
                self.crossfade_position += samples_needed
                samples_generated += samples_needed
                
                # Check if crossfade complete
                if self.crossfade_position >= self.crossfade_samples:
                    # Switch to next track
                    self.current_audio = self.next_audio
                    self.next_audio = None
                    self.current_position = samples_needed
                    self.is_crossfading = False
                    self.crossfade_position = 0
                    break
        
        # Apply master volume
        output *= self.master_volume
        
        # Soft limiting
        output = np.tanh(output * 0.95) * 0.95
        
        return output
    
    def load_song_stems(self, song_path: str, stem_volumes: dict = None) -> Optional[np.ndarray]:
        """Load and mix song stems"""
        song_dir = Path(song_path)
        if not song_dir.exists():
            print(f"❌ Song directory not found: {song_path}")
            return None
        
        if stem_volumes is None:
            stem_volumes = {'bass': 0.8, 'drums': 0.9, 'vocals': 0.8, 'piano': 0.7, 'other': 0.6}
        
        mixed_audio = None
        stems_loaded = 0
        
        for stem_name, volume in stem_volumes.items():
            stem_file = song_dir / f"{stem_name}.wav"
            if stem_file.exists():
                try:
                    stem_audio, sr = librosa.load(str(stem_file), sr=self.sample_rate, mono=False)
                    
                    # Ensure stereo
                    if stem_audio.ndim == 1:
                        stem_audio = np.stack([stem_audio, stem_audio])
                    elif stem_audio.shape[0] == 1:
                        stem_audio = np.vstack([stem_audio, stem_audio])
                    
                    # Transpose to (samples, channels)
                    stem_audio = stem_audio.T
                    
                    # Apply volume
                    stem_audio *= volume
                    
                    # Mix with other stems
                    if mixed_audio is None:
                        mixed_audio = stem_audio
                    else:
                        # Match lengths
                        min_len = min(len(mixed_audio), len(stem_audio))
                        mixed_audio = mixed_audio[:min_len] + stem_audio[:min_len]
                    
                    stems_loaded += 1
                    
                except Exception as e:
                    print(f"⚠️  Error loading {stem_name}: {e}")
        
        if mixed_audio is not None and stems_loaded > 0:
            print(f"🎵 Loaded {stems_loaded} stems from {song_dir.name}")
            # Normalize to prevent clipping
            max_val = np.max(np.abs(mixed_audio))
            if max_val > 0.95:
                mixed_audio *= 0.95 / max_val
            return mixed_audio.astype(np.float32)
        
        return None
    
    def play_song(self, song_path: str, start_crossfade_at: float = 0.8) -> bool:
        """Play a song with optional crossfade preparation"""
        with self.audio_lock:
            audio = self.load_song_stems(song_path)
            if audio is None:
                return False
            
            self.current_audio = audio
            self.current_position = 0
            self.is_playing = True
            
            return True
    
    def prepare_next_song(self, song_path: str):
        """Prepare next song for crossfading"""
        audio = self.load_song_stems(song_path)
        if audio is not None:
            with self.audio_lock:
                self.next_audio = audio
                print(f"🔄 Next song prepared: {Path(song_path).name}")
    
    def start_crossfade(self):
        """Start crossfading to next song"""
        with self.audio_lock:
            if self.next_audio is not None:
                self.is_crossfading = True
                self.crossfade_position = 0
                print("🎶 Starting crossfade...")
                return True
            return False
    
    def get_playback_info(self) -> dict:
        """Get current playback information"""
        with self.audio_lock:
            if self.current_audio is None:
                return {'playing': False}
            
            total_samples = len(self.current_audio)
            progress = self.current_position / total_samples if total_samples > 0 else 0
            remaining_time = (total_samples - self.current_position) / self.sample_rate
            
            return {
                'playing': self.is_playing,
                'progress': progress,
                'remaining_time': remaining_time,
                'crossfading': self.is_crossfading,
                'next_prepared': self.next_audio is not None
            }
    
    def stop(self):
        """Stop playback"""
        with self.audio_lock:
            self.is_playing = False
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            
    def cleanup(self):
        """Cleanup audio resources"""
        self.stop()
        self.audio.terminate()

class TSPAutoDJPlayer(TSPAutoDJ):
    """Enhanced TSP AutoDJ with real audio playback"""
    
    def __init__(self, stems_dir: str = "stems"):
        super().__init__(stems_dir)
        self.mixer = AudioMixer()
        self.playback_thread = None
        self.monitor_thread = None
        
    def play_tour_with_audio(self):
        """Play the complete TSP tour with real audio and crossfading"""
        if not self.tour:
            print("❌ No tour calculated. Run analyze_and_plan_tour() first.")
            return
        
        if not self.mixer.setup_stream():
            print("❌ Failed to setup audio stream")
            return
        
        print(f"\n🚀 Starting TSP AutoDJ with audio ({len(self.tour)} songs)")
        print("🎧 Make sure your audio is turned up!")
        print("Press Ctrl+C to stop")
        
        try:
            self.mixer.stream.start_stream()
            self._run_audio_tour()
            
        except KeyboardInterrupt:
            print("\n⏹️  Tour stopped by user")
        finally:
            self.mixer.cleanup()
    
    def _run_audio_tour(self):
        """Run the audio tour with intelligent crossfading"""
        for i, song_idx in enumerate(self.tour):
            song = self.songs[song_idx]
            
            print(f"\n🎵 Playing [{i + 1}/{len(self.tour)}]: {song.name}")
            print(f"   BPM: {song.bpm:.1f} | Key: {song.key} | Energy: {song.energy:.3f}")
            
            # Start playing current song
            if not self.mixer.play_song(song.path):
                print(f"❌ Failed to play {song.name}")
                continue
            
            # Prepare next song for crossfading
            if i + 1 < len(self.tour):
                next_idx = self.tour[i + 1]
                next_song = self.songs[next_idx]
                
                # Calculate optimal crossfade timing based on compatibility
                compatibility = self._calculate_song_compatibility(song, next_song)
                crossfade_start_ratio = 0.8 + (compatibility * 0.15)  # 80-95% through song
                
                print(f"🔄 Next: {next_song.name} (Compatibility: {compatibility:.1%})")
                
                # Monitor playback and trigger crossfade
                self._monitor_and_crossfade(next_song, crossfade_start_ratio)
            else:
                # Last song - just play to completion
                self._wait_for_song_completion()
        
        print("\n🎉 Tour completed!")
    
    def _monitor_and_crossfade(self, next_song: SongMetadata, crossfade_start: float):
        """Monitor playback and trigger crossfade at optimal time"""
        # Prepare next song
        self.mixer.prepare_next_song(next_song.path)
        
        # Monitor playback progress
        crossfade_triggered = False
        
        while True:
            info = self.mixer.get_playback_info()
            
            if not info['playing']:
                break
                
            # Trigger crossfade at optimal point
            if not crossfade_triggered and info['progress'] >= crossfade_start:
                if self.mixer.start_crossfade():
                    crossfade_triggered = True
                    print(f"🌊 Crossfading at {info['progress']:.1%}")
            
            # Check if crossfade completed or song ended
            if crossfade_triggered and not info['crossfading']:
                print("✅ Crossfade completed")
                break
            
            # Safety check - if song is almost over, break
            if info['remaining_time'] < 0.5:
                break
                
            time.sleep(0.1)
    
    def _wait_for_song_completion(self):
        """Wait for current song to finish playing"""
        while True:
            info = self.mixer.get_playback_info()
            if not info['playing'] or info['remaining_time'] < 0.1:
                break
            time.sleep(0.5)
    
    def _calculate_song_compatibility(self, song1: SongMetadata, song2: SongMetadata) -> float:
        """Calculate compatibility score between two songs (0-1, higher is better)"""
        # Key compatibility
        key_dist = CamelotWheel.key_distance(song1.key, song2.key)
        key_score = 1.0 - key_dist
        
        # BPM compatibility
        bpm_dist = BPMDistance.bpm_distance(song1.bpm, song2.bpm)
        bpm_score = 1.0 - bpm_dist
        
        # Energy compatibility
        energy_diff = abs(song1.energy - song2.energy)
        energy_score = max(0.0, 1.0 - (energy_diff / 0.2))
        
        # Weighted average
        compatibility = (key_score * 0.5 + bpm_score * 0.35 + energy_score * 0.15)
        return max(0.0, min(1.0, compatibility))
    
    def test_audio_setup(self):
        """Test audio setup with a short sample"""
        print("🔧 Testing audio setup...")
        
        if not self.mixer.setup_stream():
            return False
        
        # Generate test tone
        duration = 2.0
        freq = 440.0
        t = np.linspace(0, duration, int(self.mixer.sample_rate * duration))
        test_audio = np.sin(2 * np.pi * freq * t) * 0.3
        test_audio = np.stack([test_audio, test_audio]).T  # Make stereo
        
        print("🔊 Playing test tone for 2 seconds...")
        
        try:
            with self.mixer.audio_lock:
                self.mixer.current_audio = test_audio
                self.mixer.current_position = 0
                self.mixer.is_playing = True
            
            self.mixer.stream.start_stream()
            time.sleep(duration + 0.5)
            
            self.mixer.stop()
            print("✅ Audio test completed")
            return True
            
        except Exception as e:
            print(f"❌ Audio test failed: {e}")
            return False
        finally:
            self.mixer.cleanup()

def main():
    """Enhanced TSP AutoDJ with real audio playback"""
    print("🎯 TSP AutoDJ Player - With Real Audio Playback")
    print("=" * 55)
    
    autodj = TSPAutoDJPlayer()
    
    # Test audio first
    if not autodj.test_audio_setup():
        print("❌ Audio test failed. Check your audio setup.")
        return
    
    # Analyze and plan tour
    if not autodj.analyze_and_plan_tour():
        return
    
    # Show statistics
    autodj.show_tour_stats()
    
    # Ask user what to do
    print("\n🎮 Options:")
    print("1. Play tour with audio")
    print("2. Show tour only (no audio)")
    print("3. Exit")
    
    try:
        choice = input("\nSelect option (1-3): ").strip()
        
        if choice == "1":
            autodj.play_tour_with_audio()
        elif choice == "2":
            autodj.play_tour()
        else:
            print("👋 Goodbye!")
            
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

if __name__ == "__main__":
    main()