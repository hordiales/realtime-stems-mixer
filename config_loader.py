#!/usr/bin/env python3
"""
Configuration Loader for Eurovision Remix Engine
Handles loading and validation of mixer settings
"""

import json
import os
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from pathlib import Path

@dataclass
class AudioConfig:
    """Audio processing configuration"""
    sample_rate: int = 44100
    chunk_size: int = 512
    enable_pitch_shifting: bool = False
    enable_time_stretching: bool = True
    time_stretch_threshold: float = 0.05
    max_pitch_shift_semitones: int = 0
    soft_limiting: bool = True
    master_volume: float = 0.8

@dataclass
class MixingConfig:
    """Mixing and crossfading configuration"""
    crossfade_time: float = 4.0
    auto_normalize: bool = True
    stem_volumes: Dict[str, float] = field(default_factory=lambda: {
        'bass': 0.8, 'drums': 0.9, 'vocals': 0.8, 'piano': 0.7, 'other': 0.6
    })
    bpm_tolerance_percent: float = 15.0
    enable_bpm_matching: bool = True

@dataclass
class OSCConfig:
    """OSC control configuration"""
    port: int = 5005
    host: str = "localhost"
    enable_osc: bool = True

@dataclass
class PerformanceConfig:
    """Performance and quality settings"""
    high_quality_time_stretch: bool = True
    hop_length: int = 256
    enable_audio_effects: bool = True
    low_latency_mode: bool = False

@dataclass
class UIConfig:
    """User interface configuration"""
    show_debug_info: bool = False
    auto_start_demo: bool = False
    cli_enabled: bool = True

@dataclass
class MixerConfig:
    """Complete mixer configuration"""
    audio: AudioConfig = field(default_factory=AudioConfig)
    mixing: MixingConfig = field(default_factory=MixingConfig)
    osc: OSCConfig = field(default_factory=OSCConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    ui: UIConfig = field(default_factory=UIConfig)

class ConfigLoader:
    """Configuration loader and manager"""
    
    def __init__(self, config_file: str = "mixer_config.json"):
        self.config_file = Path(config_file)
        self.config: Optional[MixerConfig] = None
        
    def load_config(self) -> MixerConfig:
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                
                # Create config objects from loaded data
                audio_config = AudioConfig(**config_data.get('audio', {}))
                mixing_config = MixingConfig(**config_data.get('mixing', {}))
                osc_config = OSCConfig(**config_data.get('osc', {}))
                performance_config = PerformanceConfig(**config_data.get('performance', {}))
                ui_config = UIConfig(**config_data.get('ui', {}))
                
                self.config = MixerConfig(
                    audio=audio_config,
                    mixing=mixing_config,
                    osc=osc_config,
                    performance=performance_config,
                    ui=ui_config
                )
                
                print(f"✅ Loaded configuration from {self.config_file}")
                if not self.config.audio.enable_pitch_shifting:
                    print("🎵 Pitch shifting DISABLED")
                if not self.config.audio.enable_time_stretching:
                    print("⏱️  Time stretching DISABLED")
                    
                return self.config
                
            except Exception as e:
                print(f"⚠️  Error loading config: {e}")
                print("🔧 Using default configuration")
                
        else:
            print(f"📝 Config file not found: {self.config_file}")
            print("🔧 Using default configuration")
            
        # Return default config if file doesn't exist or has errors
        self.config = MixerConfig()
        return self.config
    
    def save_config(self, config: MixerConfig) -> None:
        """Save configuration to file"""
        try:
            config_dict = {
                'audio': {
                    'sample_rate': config.audio.sample_rate,
                    'chunk_size': config.audio.chunk_size,
                    'enable_pitch_shifting': config.audio.enable_pitch_shifting,
                    'enable_time_stretching': config.audio.enable_time_stretching,
                    'time_stretch_threshold': config.audio.time_stretch_threshold,
                    'max_pitch_shift_semitones': config.audio.max_pitch_shift_semitones,
                    'soft_limiting': config.audio.soft_limiting,
                    'master_volume': config.audio.master_volume
                },
                'mixing': {
                    'crossfade_time': config.mixing.crossfade_time,
                    'auto_normalize': config.mixing.auto_normalize,
                    'stem_volumes': config.mixing.stem_volumes,
                    'bpm_tolerance_percent': config.mixing.bpm_tolerance_percent,
                    'enable_bpm_matching': config.mixing.enable_bpm_matching
                },
                'osc': {
                    'port': config.osc.port,
                    'host': config.osc.host,
                    'enable_osc': config.osc.enable_osc
                },
                'performance': {
                    'high_quality_time_stretch': config.performance.high_quality_time_stretch,
                    'hop_length': config.performance.hop_length,
                    'enable_audio_effects': config.performance.enable_audio_effects,
                    'low_latency_mode': config.performance.low_latency_mode
                },
                'ui': {
                    'show_debug_info': config.ui.show_debug_info,
                    'auto_start_demo': config.ui.auto_start_demo,
                    'cli_enabled': config.ui.cli_enabled
                }
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config_dict, f, indent=2)
                
            print(f"💾 Configuration saved to {self.config_file}")
            
        except Exception as e:
            print(f"❌ Error saving config: {e}")
    
    def create_default_config(self) -> None:
        """Create a default configuration file"""
        default_config = MixerConfig()
        self.save_config(default_config)
    
    def show_current_config(self) -> None:
        """Display current configuration"""
        if not self.config:
            self.load_config()
            
        print("\n🎛️  CURRENT MIXER CONFIGURATION")
        print("=" * 50)
        
        print("\n🎵 Audio Settings:")
        print(f"  Sample Rate: {self.config.audio.sample_rate} Hz")
        print(f"  Buffer Size: {self.config.audio.chunk_size} samples")
        print(f"  Pitch Shifting: {'ENABLED' if self.config.audio.enable_pitch_shifting else 'DISABLED'}")
        print(f"  Time Stretching: {'ENABLED' if self.config.audio.enable_time_stretching else 'DISABLED'}")
        print(f"  Master Volume: {self.config.audio.master_volume:.2f}")
        
        print("\n🎚️ Mixing Settings:")
        print(f"  Crossfade Time: {self.config.mixing.crossfade_time:.1f}s")
        print(f"  BPM Matching: {'ENABLED' if self.config.mixing.enable_bpm_matching else 'DISABLED'}")
        print(f"  BPM Tolerance: {self.config.mixing.bpm_tolerance_percent:.1f}%")
        
        print("\n🎛️  OSC Settings:")
        print(f"  OSC Control: {'ENABLED' if self.config.osc.enable_osc else 'DISABLED'}")
        print(f"  Host: {self.config.osc.host}")
        print(f"  Port: {self.config.osc.port}")
        
        print("\n⚡ Performance Settings:")
        print(f"  High Quality: {'ENABLED' if self.config.performance.high_quality_time_stretch else 'DISABLED'}")
        print(f"  Low Latency: {'ENABLED' if self.config.performance.low_latency_mode else 'DISABLED'}")
        print(f"  Hop Length: {self.config.performance.hop_length}")

def main():
    """Configuration management CLI"""
    import sys
    
    config_loader = ConfigLoader()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'show':
            config_loader.show_current_config()
        elif command == 'create':
            config_loader.create_default_config()
            print("✅ Default configuration file created")
        elif command == 'disable-pitch':
            config = config_loader.load_config()
            config.audio.enable_pitch_shifting = False
            config.audio.max_pitch_shift_semitones = 0
            config_loader.save_config(config)
            print("🎵 Pitch shifting disabled")
        elif command == 'enable-pitch':
            config = config_loader.load_config()
            config.audio.enable_pitch_shifting = True
            config.audio.max_pitch_shift_semitones = 12
            config_loader.save_config(config)
            print("🎵 Pitch shifting enabled")
        elif command == 'low-latency':
            config = config_loader.load_config()
            config.performance.low_latency_mode = True
            config.audio.chunk_size = 256
            config_loader.save_config(config)
            print("⚡ Low latency mode enabled")
        else:
            print("❌ Unknown command")
            print("Usage: python config_loader.py [show|create|disable-pitch|enable-pitch|low-latency]")
    else:
        print("🎛️  Eurovision Mixer Configuration")
        print("Available commands:")
        print("  show         - Show current configuration")
        print("  create       - Create default config file")
        print("  disable-pitch - Disable pitch shifting")
        print("  enable-pitch  - Enable pitch shifting") 
        print("  low-latency   - Enable low latency mode")

if __name__ == "__main__":
    main()