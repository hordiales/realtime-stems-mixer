#!/usr/bin/env python3
"""
DJ Plan Executor for SuperCollider
Execute remix plans created by demo_mixer.py in real-time with SuperCollider like a professional DJ
"""

import json
import time
import threading
from pathlib import Path
from pythonosc import udp_client
from typing import Dict, List, Any
import argparse

# Try to import audio libraries for duration detection
try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

class DJPlanExecutor:
    """Execute DJ remix plans with SuperCollider like a professional DJ"""
    
    def __init__(self, sc_host: str = "localhost", sc_port: int = 57120):
        self.sc_host = sc_host
        self.sc_port = sc_port
        self.sc_client = udp_client.SimpleUDPClient(sc_host, sc_port)
        
        # State tracking
        self.loaded_buffers: Dict[str, int] = {}
        self.next_buffer_id = 1000
        self.current_section = 0
        self.playing = False
        self.plan_data = None
        
        print(f"🎧🎛️ DJ Plan Executor initialized")
        print(f"🔌 SuperCollider: {sc_host}:{sc_port}")
        
        # Test connection
        try:
            self.sc_client.send_message("/test_tone", [440])
            print("✅ SuperCollider connection test sent")
        except Exception as e:
            print(f"⚠️  Could not test SuperCollider connection: {e}")
    
    def load_plan(self, json_file: str) -> bool:
        """Load JSON remix plan from file"""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                self.plan_data = json.load(f)
            
            print(f"📄 Loaded plan: {json_file}")
            print(f"🎵 Theme: {self.plan_data.get('theme', 'unknown')}")
            print(f"🎤 Base: {self.plan_data.get('base_song', 'unknown')}")
            print(f"🎼 BPM: {self.plan_data.get('base_bpm', '?')}")
            print(f"🎹 Key: {self.plan_data.get('base_key', '?')}")
            print(f"🏗️  Structure: {' → '.join(self.plan_data.get('structure', []))}")
            
            sections = self.plan_data.get('sections', {})
            print(f"📊 Sections: {len(sections)}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error loading plan: {e}")
            return False
    
    def _get_buffer_id(self, file_path: str) -> int:
        """Get or create buffer ID for file"""
        if file_path in self.loaded_buffers:
            return self.loaded_buffers[file_path]
        
        buffer_id = self.next_buffer_id
        self.next_buffer_id += 1
        self.loaded_buffers[file_path] = buffer_id
        return buffer_id
    
    def _get_audio_duration(self, file_path: str) -> float:
        """Get duration of audio file in seconds"""
        try:
            full_path = Path(file_path).absolute()
            if not full_path.exists():
                print(f"⚠️  File not found for duration check: {full_path}")
                return 30.0  # Default fallback
            
            # Try soundfile first (faster)
            if SOUNDFILE_AVAILABLE:
                try:
                    info = sf.info(str(full_path))
                    duration = info.frames / info.samplerate
                    return duration
                except Exception as e:
                    print(f"⚠️  Soundfile duration failed: {e}")
            
            # Try librosa as fallback
            if LIBROSA_AVAILABLE:
                try:
                    duration = librosa.get_duration(filename=str(full_path))
                    return duration
                except Exception as e:
                    print(f"⚠️  Librosa duration failed: {e}")
            
            # If no audio libraries available, use rough estimate based on file size
            file_size_mb = full_path.stat().st_size / (1024 * 1024)
            # Rough estimate: ~1MB per 8 seconds for 44.1kHz stereo (varies by compression)
            estimated_duration = file_size_mb * 8
            print(f"⚠️  Using file size estimate: {estimated_duration:.1f}s")
            return estimated_duration
            
        except Exception as e:
            print(f"⚠️  Duration detection failed: {e}, using default 30s")
            return 30.0
    
    def _get_section_duration(self, section_data: Dict[str, Any]) -> float:
        """Calculate the duration of a section based on its stems"""
        stems = section_data.get('stems', {})
        if not stems:
            return 30.0  # Default fallback
        
        # Get duration of the first stem file (they should all be similar length)
        first_stem = list(stems.values())[0]
        file_path = first_stem['file']
        
        duration = self._get_audio_duration(file_path)
        print(f"📏 Section duration: {duration:.1f}s")
        return duration
    
    def _load_stem_buffer(self, stem_info: Dict[str, Any], stem_type: str) -> int:
        """Load individual stem buffer with memory optimization"""
        file_path = stem_info['file']
        song_name = stem_info['song'].split('(')[0].strip()
        
        buffer_id = self._get_buffer_id(file_path)
        stem_name = f"{song_name}_{stem_type}"
        
        # Send load command to SuperCollider
        try:
            full_path = Path(file_path).absolute()
            if not full_path.exists():
                print(f"❌ File not found: {full_path}")
                return None
            
            # Check file size for memory awareness
            file_size_mb = full_path.stat().st_size / (1024 * 1024)
            if file_size_mb > 50:  # Warn about large files
                print(f"⚠️  Large file: {stem_name} ({file_size_mb:.1f} MB)")
                
            self.sc_client.send_message("/load_buffer", [
                buffer_id,
                str(full_path),
                stem_name
            ])
            print(f"📥 Loading: {stem_name} → buffer {buffer_id} ({file_size_mb:.1f}MB)")
            return buffer_id
            
        except Exception as e:
            print(f"❌ Error loading {stem_name}: {e}")
            return None
    
    def _play_stem_buffer(self, buffer_id: int, stem_info: Dict[str, Any], volume: float = 0.8):
        """Play stem buffer with correct rate/pitch"""
        if buffer_id is None:
            print("❌ Invalid buffer ID (None)")
            return
            
        try:
            pitch_shift = stem_info.get('pitch_shift', 1.0)
            rate = pitch_shift  # Use pitch_shift as playback rate
            loop = 1  # Always loop for continuous playback
            start_pos = 0.0  # Start from beginning
            
            # Validate parameters
            if not isinstance(buffer_id, int) or buffer_id < 1000:
                print(f"❌ Invalid buffer ID: {buffer_id}")
                return
                
            # Match SuperCollider OSC message format exactly:
            # /play_stem [bufferID, rate, volume, loop, startPos]
            # Wait a bit to ensure buffer is loaded
            time.sleep(0.3)
            
            message_params = [
                int(buffer_id),  # Ensure integer
                float(rate),
                float(volume), 
                int(loop),
                float(start_pos)
            ]
            
            print(f"🎵 Sending OSC: /play_stem {message_params}")
            self.sc_client.send_message("/play_stem", message_params)
            
            song_name = stem_info['song'].split('(')[0].strip()
            rate_info = f"(rate: {rate:.3f})" if rate != 1.0 else ""
            print(f"▶️  Playing: {song_name} {rate_info} vol:{volume:.2f}")
            
        except Exception as e:
            print(f"❌ Error playing buffer {buffer_id}: {e}")
    
    def play_section(self, section_key: str, auto_advance: bool = False):
        """Play a specific section from the plan"""
        if not self.plan_data:
            print("❌ No plan loaded")
            return False
        
        sections = self.plan_data.get('sections', {})
        if section_key not in sections:
            print(f"❌ Section '{section_key}' not found")
            return False
        
        section = sections[section_key]
        section_type = section.get('type', 'unknown')
        stems = section.get('stems', {})
        
        print(f"\n🎵 PLAYING SECTION: {section_key.upper()} ({section_type})")
        print("=" * 50)
        
        # Stop any currently playing stems first (memory optimization)
        try:
            self.sc_client.send_message("/mixer_cleanup", [])
            print("🧹 Cleaned previous stems for memory optimization")
            time.sleep(0.5)
        except:
            pass
        
        # Load and play stems one by one for memory efficiency
        active_buffers = []
        
        for stem_type, stem_info in stems.items():
            buffer_id = self._load_stem_buffer(stem_info, stem_type)
            if buffer_id is not None and buffer_id > 0:
                active_buffers.append((buffer_id, stem_info))
                print(f"✅ Buffer ready: {buffer_id}")
            else:
                print(f"❌ Failed to prepare buffer for {stem_type}")
        
        # Wait for all buffers to load
        print("⏳ Waiting for buffers to load...")
        time.sleep(3)  # Longer wait to ensure all buffers are ready
        
        # Now play all loaded stems with proper volumes
        for buffer_id, stem_info in active_buffers:
            # Adjust volume based on stem type for better mix
            stem_volume = 0.7  # Base volume
            if 'drums' in stem_info.get('song', '').lower():
                stem_volume = 0.8  # Drums slightly louder
            elif 'vocal' in stem_info.get('song', '').lower():
                stem_volume = 0.9  # Vocals prominent
            
            self._play_stem_buffer(buffer_id, stem_info, stem_volume)
            time.sleep(0.2)  # Slightly longer delay for stability
        
        # Set initial crossfade (deck A active for stems below 1100, deck B for above)
        try:
            # Determine which deck to use based on buffer IDs
            has_deck_a = any(buf_id < 1100 for buf_id, _ in active_buffers)
            has_deck_b = any(buf_id >= 1100 for buf_id, _ in active_buffers)
            
            deck_a_vol = 0.8 if has_deck_a else 0.0
            deck_b_vol = 0.8 if has_deck_b else 0.0
            
            self.sc_client.send_message("/crossfade_levels", [deck_a_vol, deck_b_vol])
            print(f"🎚️  Crossfade: A:{deck_a_vol} B:{deck_b_vol}")
        except Exception as e:
            print(f"⚠️  Crossfade error: {e}")
        
        print(f"✅ Section started with {len(active_buffers)} stems")
        
        # Auto-advance to next section after actual duration
        if auto_advance:
            # Get the actual duration of this section
            section_duration = self._get_section_duration(section)
            
            structure = self.plan_data.get('structure', [])
            current_idx = None
            
            # Find current section in structure
            for i, struct_type in enumerate(structure):
                if section_key.endswith(struct_type) or struct_type in section_key:
                    current_idx = i
                    break
            
            if current_idx is not None and current_idx + 1 < len(structure):
                next_section_type = structure[current_idx + 1]
                # Find next section with this type
                next_key = None
                for key in sections.keys():
                    if next_section_type in key and key > section_key:
                        next_key = key
                        break
                
                if next_key:
                    print(f"⏭️  Auto-advancing to {next_key} in {section_duration:.1f} seconds...")
                    threading.Timer(section_duration, lambda: self.play_section(next_key, True)).start()
        
        return True
    
    def play_full_plan(self):
        """Play the entire remix plan automatically with memory optimization"""
        if not self.plan_data:
            print("❌ No plan loaded")
            return
        
        sections = self.plan_data.get('sections', {})
        structure = self.plan_data.get('structure', [])
        
        # Calculate total estimated duration based on actual file lengths
        total_duration = 0
        for section_key in sorted(sections.keys()):
            section_duration = self._get_section_duration(sections[section_key])
            total_duration += section_duration
        
        print(f"\n🎭 PLAYING FULL REMIX PLAN (Memory Optimized)")
        print(f"🎵 Theme: {self.plan_data.get('theme', '').upper()}")
        print(f"⏱️  Total duration: {total_duration:.1f} seconds ({total_duration/60:.1f} minutes)")
        print("💾 Memory: Buffers freed between sections")
        print("=" * 60)
        
        # Play sections in order
        section_keys = sorted(sections.keys())
        
        for i, section_key in enumerate(section_keys):
            auto_advance = (i < len(section_keys) - 1)  # Don't auto-advance on last section
            section_data = sections[section_key]
            
            self.play_section(section_key, auto_advance)
            
            if not auto_advance:
                print("\n🎉 REMIX COMPLETE!")
                # Final cleanup
                try:
                    self.sc_client.send_message("/mixer_cleanup", [])
                    print("🧹 Final cleanup completed")
                except:
                    pass
                break
            else:
                # Wait for actual section duration
                section_duration = self._get_section_duration(section_data)
                print(f"⏳ Playing for {section_duration:.1f} seconds...")
                
                # Wait most of the time, then check memory
                wait_time = max(5, section_duration - 5)  # Wait at least 5s, but leave 5s for status check
                time.sleep(wait_time)
                
                # Check server status before next section
                try:
                    self.sc_client.send_message("/get_status", [])
                except:
                    pass
                
                # Wait remaining time
                remaining_time = section_duration - wait_time
                if remaining_time > 0:
                    time.sleep(remaining_time)
    
    def show_plan_info(self):
        """Display detailed plan information"""
        if not self.plan_data:
            print("❌ No plan loaded")
            return
        
        print(f"\n📄 REMIX PLAN DETAILS")
        print("=" * 50)
        print(f"Theme: {self.plan_data.get('theme', 'unknown').upper()}")
        print(f"Base Song: {self.plan_data.get('base_song', 'unknown')}")
        print(f"Base BPM: {self.plan_data.get('base_bpm', '?')}")
        print(f"Base Key: {self.plan_data.get('base_key', '?')}")
        
        structure = self.plan_data.get('structure', [])
        print(f"\\nStructure ({len(structure)} sections):")
        for i, section_type in enumerate(structure):
            print(f"  {i+1:2d}. {section_type}")
        
        sections = self.plan_data.get('sections', {})
        print(f"\\nDetailed Sections ({len(sections)}):")
        
        for section_key, section_data in sorted(sections.items()):
            section_type = section_data.get('type', 'unknown')
            stems = section_data.get('stems', {})
            duration = self._get_section_duration(section_data)
            
            print(f"\\n  📊 {section_key.upper()} ({section_type}) - {duration:.1f}s")
            
            for stem_type, stem_info in stems.items():
                song = stem_info['song'].split('(')[0].strip()
                bpm = stem_info.get('bpm', '?')
                key = stem_info.get('key', '?')
                pitch = stem_info.get('pitch_shift', 1.0)
                timestretch = "🔄" if stem_info.get('needs_timestretch', False) else ""
                
                pitch_info = f"×{pitch:.3f}" if pitch != 1.0 else "×1.000"
                print(f"    {stem_type:6s}: {song:20s} {str(bpm):>3s}bpm {key:2s} {pitch_info} {timestretch}")
    
    def interactive_mode(self):
        """Interactive section selection"""
        if not self.plan_data:
            print("❌ No plan loaded")
            return
        
        sections = self.plan_data.get('sections', {})
        section_keys = sorted(sections.keys())
        
        print(f"\\n🎛️ INTERACTIVE PLAN EXECUTION")
        print("Available commands:")
        print("  info           - Show plan details")
        print("  list           - List all sections")
        print("  play <section> - Play specific section")
        print("  full           - Play full plan automatically")
        print("  stop           - Stop all audio and free memory")
        print("  status         - Check SuperCollider server status")
        print("  quit           - Exit")
        print()
        
        while True:
            try:
                cmd = input("🎧🎛️ > ").strip().lower()
                if not cmd:
                    continue
                
                parts = cmd.split()
                command = parts[0]
                
                if command == "quit":
                    break
                elif command == "info":
                    self.show_plan_info()
                elif command == "list":
                    print("\\n📋 Available sections:")
                    for i, key in enumerate(section_keys):
                        section_type = sections[key].get('type', 'unknown')
                        stem_count = len(sections[key].get('stems', {}))
                        print(f"  {i+1:2d}. {key} ({section_type}, {stem_count} stems)")
                elif command == "play" and len(parts) >= 2:
                    section_arg = parts[1]
                    # Allow playing by number or name
                    if section_arg.isdigit():
                        idx = int(section_arg) - 1
                        if 0 <= idx < len(section_keys):
                            self.play_section(section_keys[idx])
                        else:
                            print(f"❌ Invalid section number: {section_arg}")
                    else:
                        # Find section by partial name match
                        matches = [key for key in section_keys if section_arg in key.lower()]
                        if len(matches) == 1:
                            self.play_section(matches[0])
                        elif len(matches) > 1:
                            print(f"❌ Multiple matches: {matches}")
                        else:
                            print(f"❌ Section not found: {section_arg}")
                elif command == "full":
                    self.play_full_plan()
                elif command == "stop":
                    try:
                        self.sc_client.send_message("/mixer_cleanup", [])
                        print("⏹️  Stopped all audio and freed memory")
                        # Clear our tracking too
                        self.loaded_buffers.clear()
                    except Exception as e:
                        print(f"❌ Error stopping: {e}")
                elif command == "status":
                    try:
                        self.sc_client.send_message("/get_status", [])
                        print("📊 Requested server status (check SuperCollider window)")
                    except Exception as e:
                        print(f"❌ Error requesting status: {e}")
                else:
                    print("❌ Unknown command")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Error: {e}")
        
        print("👋 Interactive mode ended")

def main():
    parser = argparse.ArgumentParser(description='Execute DJ remix plans with SuperCollider like a professional DJ')
    parser.add_argument('json_file', help='JSON remix plan file')
    parser.add_argument('--host', default='localhost', help='SuperCollider host')
    parser.add_argument('--port', type=int, default=57120, help='SuperCollider port')
    parser.add_argument('--mode', choices=['interactive', 'full', 'info'], default='interactive',
                        help='Execution mode')
    
    args = parser.parse_args()
    
    executor = DJPlanExecutor(args.host, args.port)
    
    if not executor.load_plan(args.json_file):
        return 1
    
    if args.mode == 'info':
        executor.show_plan_info()
    elif args.mode == 'full':
        executor.play_full_plan()
    else:
        executor.interactive_mode()
    
    return 0

if __name__ == "__main__":
    exit(main())