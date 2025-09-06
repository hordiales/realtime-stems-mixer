# Eurovision Music Mixing Engine 🎵

A sophisticated real-time music mixing engine that combines stems from different Eurovision songs based on BPM compatibility, key harmony, and musical structure using the Camelot Wheel system.

## Features

### 🎼 Musical Intelligence
- **BPM Matching**: Compatible songs within 5-15% BPM tolerance
- **Key Compatibility**: Uses Camelot Wheel system for harmonic mixing
- **Music Theory**: Supports relative major/minor keys and perfect fifths
- **Automatic Key Estimation**: Based on BPM and song characteristics

### 🎛️ Mixing Capabilities
- **Stem Separation**: Works with bass, drums, vocals, piano, and other stems
- **Song Structure Analysis**: Understands verse, chorus, bridge, intro, outro sections  
- **Intelligent Stem Selection**: Different strategies per mixing theme
- **Time-stretching Detection**: Identifies when pitch/tempo adjustment needed

### 🎨 Themed Remixes
- **Energetic**: High-energy combinations with driving rhythms
- **Chill**: Smooth, lower BPM mixes with consistent flow
- **Dramatic**: Dynamic contrasts and emotional builds

## File Structure

```
Eurovision/
├── stems/                          # Individual song stem directories
│   ├── 01-01 Zjerm.../
│   │   ├── bass.wav
│   │   ├── drums.wav
│   │   ├── vocals.wav
│   │   ├── piano.wav
│   │   └── other.wav
│   └── ...
├── song-structures/                # Song metadata and structure
│   ├── 01-01 Zjerm....json        # BPM, beats, segments
│   └── ...
├── music_mixer.py                  # Basic mixing engine
├── advanced_mixer.py              # Advanced engine with key detection
├── demo_mixer.py                  # Demo script and examples
└── README.md                      # This file
```

## Song Database

The engine currently includes **11 Eurovision 2025 songs** with BPMs ranging from 67-154:

### By BPM Clusters:
- **60-80 BPM**: Wasted Love (67)
- **80-100 BPM**: Poison Cake (86), Zjerm (95)
- **100-120 BPM**: Run With U (115)
- **120-140 BPM**: Espresso Macchiato (120), Kiss Kiss Goodbye (125), SURVIVOR (133)
- **140-160 BPM**: Hallucination (140), Shh (143), Strobe Lights (146), Milkshake Man (154)

### Key Distribution:
- **Major Keys**: C, D, E, F, G, A, B
- **Minor Keys**: Am, Dm, Em
- **Compatible Groups**: Automatically detected using Camelot Wheel

## Usage

### Basic Usage
```python
from advanced_mixer import AdvancedMusicMixer

# Initialize mixer
mixer = AdvancedMusicMixer("stems", "song-structures")

# Create themed remix
remix = mixer.create_intelligent_remix("energetic")
mixer.print_advanced_remix_plan(remix)
```

### Quick Demo
```bash
python demo_mixer.py
```

### Example Output
```
🎵 ADVANCED REMIX PLAN - ENERGETIC THEME 🎵
Base Song: Hallucination (Eurovision 2025 - Denmark)
Base BPM: 140 | Base Key: D
Compatible Songs: Shh (Eurovision 2025 - Cyprus)
Structure: intro → verse → chorus → verse → bridge → chorus → chorus → outro

Section Details:
00_INTRO: INTRO
  bass     -> Shh                  (BPM: 143, Key: A  , Shift: 0.98)
  drums    -> Shh                  (BPM: 143, Key: A  , Shift: 0.98)
  vocals   -> Hallucination        (BPM: 140, Key: D  , Shift: 1.00)
```

## Mixing Criteria

### BPM Compatibility
- **Strict Mode**: ±5% tolerance (for seamless beatmatching)
- **Relaxed Mode**: ±15% tolerance (for creative mixing)
- **Time-stretching**: Automatically detected when pitch shift > 5%

### Key Compatibility (Camelot Wheel)
- **Adjacent Keys**: ±1 position on wheel (smooth transitions)
- **Relative Major/Minor**: Same number, different letter
- **Perfect Fifths**: ±7 positions (harmonic compatibility)

### Stem Selection Strategies

#### Energetic Theme
- Prioritizes higher BPM drums and bass
- Maintains consistent vocals
- Creates driving, high-energy feel

#### Chill Theme  
- Favors lower, consistent BPMs
- Smooth stem transitions
- Relaxed, flowing atmosphere

#### Dramatic Theme
- Creates dynamic contrasts
- Mixes high and low energy elements
- Builds emotional intensity

## Technical Details

### Song Structure Format
```json
{
  "bpm": 140,
  "beats": [0.82, 1.24, 1.7, ...],
  "downbeats": [1.7, 3.44, 5.19, ...],
  "segments": [
    {"start": 0.82, "end": 15.62, "label": "intro"},
    {"start": 15.62, "end": 29.53, "label": "verse"},
    ...
  ]
}
```

### Remix Plan Output
```json
{
  "theme": "energetic",
  "base_song": "Hallucination",
  "base_bpm": 140,
  "base_key": "D",
  "structure": ["intro", "verse", "chorus", ...],
  "sections": {
    "00_intro": {
      "stems": {
        "bass": {"song": "...", "bpm": 143, "pitch_shift": 0.98}
      }
    }
  }
}
```

## Advanced Features

### Key Detection
- Automatic key estimation based on BPM and musical characteristics
- Eurovision-specific key mapping for dance/pop songs
- Harmonic compatibility analysis

### Real-time Capabilities  
- Efficient stem file detection
- Fast compatibility calculations
- Optimized for live performance use

### Export Options
- JSON remix plans for external audio software
- Detailed technical specifications for each stem
- Time-stretching and pitch-shift information

## Next Steps

### Audio Processing
- Implement actual audio mixing with librosa/pydub
- Real-time stem playback and crossfading
- Audio effects (reverb, EQ, compression)

### Enhanced Features
- Machine learning key detection from audio
- Automatic beat-matching and synchronization
- Web-based interface for live mixing

### Performance Optimization
- Caching for large stem libraries
- Parallel processing for multiple remixes
- Memory-efficient audio streaming

## Requirements

- Python 3.7+
- JSON support (built-in)
- Audio files in WAV format
- Song structure metadata in JSON format

## Contributing

The engine is designed to be extensible:
- Add new compatibility algorithms
- Implement additional mixing themes
- Extend key detection systems
- Add support for other audio formats

## License

This project demonstrates advanced music mixing concepts using Eurovision 2025 data for educational and research purposes.