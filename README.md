# Eurovision Music Mixing Engine 🎵

A **real-time** music mixing engine that combines stems from different Eurovision songs. Features both intelligent offline planning and **live SuperCollider-based mixing** with smart memory management.

***
Demo: Livecoding session, mixing stems from different songs:
https://youtu.be/1cXhiNixB_o
***

Check the full [CrowdStream](https://timmd-9216.github.io/crowdstream/) project for another experimental uses and details.

## 🚀 **Latest Features - SuperCollider Integration**

- **Real-Time Audio Mixing**: Live stem playback via SuperCollider audio server
- **Smart Memory Loading**: Only loads stems when playing (optimized for 16GB RAM)
- **Individual Stem Control**: Mix bass from one song with drums from another
- **Section-Based Playback**: Play specific sections (verse, chorus, bridge, etc.)
- **High-Quality Audio**: 44.1kHz matching, no resampling degradation
- **OSC Control**: External control via OSC messages

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
├── stems/                                    # Individual song stem directories
│   ├── 01-01 Zjerm.../
│   │   ├── bass.wav
│   │   ├── drums.wav
│   │   ├── vocals.wav
│   │   ├── piano.wav
│   │   └── other.wav
│   └── ...
├── song-structures/                          # Song metadata and structure
│   ├── 01-01 Zjerm....json                 # BPM, beats, segments
│   └── ...
├── 🧠 supercollider_stem_mixer_smart.py    # ✅ SMART LOADING REAL-TIME MIXER
├── 🎛️ supercollider_audio_server_minimal.scd # ✅ HIGH-QUALITY AUDIO SERVER
├── doc/SMART_STEM_MIXER_GUIDE.md               # Complete usage guide
├── doc/OSC_MESSAGES_REFERENCE.md               # OSC protocol reference
└── README.md                               # This file
```

**IMPORTANT NOTE:** for a reliable stems separation use demucs/spleeter and for song structure [allinone](https://github.com/hordiales/all-in-one) (which also does stems split using demucs)

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

### 🎛️ **Real-Time Smart Mixer (Recommended)**

**1. Start SuperCollider Audio Server:**
```supercollider
// In SuperCollider IDE:
s.quit; s.reboot;  // Clean restart
"supercollider_audio_server_minimal.scd".loadRelative;
```

**2. Run Smart Mixer:**
```bash
python supercollider_stem_mixer_smart.py
```

**3. Live Mixing Commands:**
```bash
🎛️🧠 > songs                    # List available songs
🎛️🧠 > a.bass 2                # Load bass from song 2 to deck A
🎛️🧠 > b.vocals.chorus 5       # Load vocals from chorus of song 5 to deck B
🎛️🧠 > bpm 128                 # Set BPM to 128
🎛️🧠 > cross 0.5               # 50/50 crossfade between decks
🎛️🧠 > bass 0.8                # Set bass volume to 80%
🎛️🧠 > random                  # Generate random creative mix
```

**See [`SMART_STEM_MIXER_GUIDE.md`](SMART_STEM_MIXER_GUIDE.md) for complete documentation.**

### 🤖 **Intelligent Offline Planning**
```python
from advanced_mixer import AdvancedMusicMixer

# Initialize mixer
mixer = AdvancedMusicMixer("stems", "song-structures")

# Create themed remix
remix = mixer.create_intelligent_remix("energetic")
mixer.print_advanced_remix_plan(remix)
```

### 🎵 **Quick Demo**
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

### 🧠 **Smart Loading System**
- **Memory Efficient**: Only loads stems when actually playing
- **Automatic Cleanup**: Frees unused buffers automatically
- **16GB Optimized**: Perfect for systems with limited RAM
- **Buffer Management**: Smart allocation and deallocation

### 🎛️ **Real-Time Audio Engine**
- **High-Quality**: 44.1kHz native, no resampling degradation  
- **Low Latency**: 256-sample blocks for responsive control
- **Individual Control**: Each stem controllable independently
- **Section Playback**: Jump to specific song sections (verse, chorus, etc.)

### 🎵 **Musical Intelligence**
- **BPM Sync**: Automatic tempo matching across stems
- **Key Detection**: Eurovision-specific key mapping
- **Structure Analysis**: Understands song sections and timing
- **Harmonic Mixing**: Camelot Wheel compatibility

### 📡 **OSC Integration**
- **External Control**: Full OSC message support
- **Real-Time**: Instant parameter changes
- **Automation Ready**: Perfect for live performance
- **Protocol Documentation**: Complete OSC reference available

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

### 🧠 **Smart Real-Time Mixer**
- **SuperCollider** 3.12+ (audio server)
- **Python 3.7+** with dependencies:
  - `pythonosc` - OSC communication
  - `pathlib` - File handling
  - `json` - Configuration
- **Audio Files**: WAV format, 44.1kHz stereo preferred
- **Memory**: 16GB+ RAM recommended
- **Song Structures**: JSON metadata files

### 📦 **Installation**
```bash
# Install SuperCollider from: https://supercollider.github.io/
# Install Python dependencies:
pip install python-osc pathlib
```

## Contributing

The engine is designed to be extensible:
- Add new compatibility algorithms
- Implement additional mixing themes
- Extend key detection systems
- Add support for other audio formats

## License

This project demonstrates advanced music mixing concepts using Eurovision 2025 data for educational and research purposes.