# Music Mixing Engine 🎵

A **real-time** music mixing engine that combines stems from different songs sections (intro, verse, chorus, etc). Features both intelligent offline planning with smart memory/resources management.

***
Demo: Livecoding session, mixing stems from different Eurovision songs:
https://youtu.be/1cXhiNixB_o
***

Check the full [CrowdStream](https://timmd-9216.github.io/crowdstream/) project for another experimental uses and details.

## 🚀 **Latest Features - Interactive TSP AutoDJ with Real-time Stem Swapping**

- **TSP Song Optimization**: Traveling Salesman Problem finds optimal song order using Camelot wheel + BPM compatibility
- **Real-Time Stem Swapping**: Live replacement of individual instruments during playback with automatic key/BPM adjustment
- **Country-Based Stem Selection**: Use country names as identifiers - `swap bass albania`, `swap drums croatia`
- **Interactive Command Line**: Live control while music plays - change any stem from any Eurovision country
- **Automatic Harmonic Mixing**: Pitch shifting and time stretching for seamless stem compatibility
- **Smart Memory Loading**: Only loads stems when playing (optimized for 16GB RAM)
- **Camelot Wheel Integration**: Professional DJ-style harmonic mixing with Eurovision song database
- **High-Quality Audio**: 44.1kHz native, no resampling degradation

## Features

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
├── song-structures/                          # Song metadata and structure (38 songs)
│   ├── 01-01 Zjerm....json                 # BPM, beats, segments
│   ├── 01-11 Espresso Macchiato....json    # Eurovision 2025 songs
│   └── ...
├── 🎯 tsp_autodj.py                        # ✅ TSP SONG OPTIMIZER & ANALYZER  
├── 🎛️ interactive_tsp_mixer.py             # ✅ INTERACTIVE STEM SWAPPING MIXER
├── 🎮 interactive_mixer_demo.py            # ✅ DEMO OF COUNTRY-BASED STEM SWAPPING
├── 🧠 stem_mixer_smart.py                  # ✅ SMART LOADING REAL-TIME MIXER
├── 🐍 audio_server.py                      # ✅ PYTHON AUDIO ENGINE
├── 🚀 start_python_mixer.sh                # ✅ ONE-CLICK PYTHON MIXER LAUNCHER
├── 📋 config_loader.py                     # Configuration management
├── 🔧 mixer_config.json                    # Mixer settings
├── supercollider-engine/                    # SuperCollider audio server option
│   ├── supercollider_audio_server_minimal.scd # High-quality audio server
│   └── run_audio_server.scd                # Server launcher
├── autodj-plan/                             # Intelligent offline mixing
│   ├── advanced_mixer.py                   # Music intelligence engine
│   ├── demo_mixer.py                       # Demo plan generator
│   ├── dj_plan_executor.py                 # Execute remix plans
│   ├── start_python_dj.sh                  # Launch DJ system
│   ├── remix_*.json                        # Example remix plans
│   └── DJ_PLAN_EXECUTION_GUIDE.md          # DJ system guide
├── docs/                                    # Complete documentation
│   ├── SMART_STEM_MIXER_GUIDE.md           # Smart mixer usage
│   ├── OSC_MESSAGES_REFERENCE.md           # OSC protocol reference
│   ├── README_PYTHON_AUDIO.md              # Python audio engine docs
│   └── SUPERCOLLIDER_MIXER_GUIDE.md        # SuperCollider guide
├── tests/                                   # Testing framework
│   ├── test_audio_server.py                # Audio server tests
│   └── test_sc_direct.py                   # SuperCollider tests
├── utils/                                   # Utility scripts
│   ├── start_python_mixer.py               # Advanced Python launcher
│   └── kill_servers.py                     # Server cleanup utility
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

### 🎯 **Interactive TSP AutoDJ with Country-Based Stem Swapping (NEW!)**

**🎮 Quick Start with Demo:**
```bash
python interactive_mixer_demo.py
```

**🎛️ Real-Time Country-Based Stem Commands:**
```bash
# Start the interactive TSP mixer
python interactive_tsp_mixer.py

# In the interactive CLI:
play                          # Start TSP-optimized song tour
swap bass albania             # Replace current bass with Albania's bass stem
swap drums croatia            # Use Croatia's drums (auto-adjusted for key/BPM)
swap vocals denmark           # Use Denmark's vocals with harmonic matching
swap piano estonia            # Use Estonia's piano part
find vocals 4A 120            # Find vocals compatible with key 4A @ 120 BPM
volume drums 1.5              # Set drums volume to 150%
mute vocals                   # Mute vocals from any country
status                        # Show current mix status
list songs                    # Show all Eurovision countries
quit                          # Exit mixer
```

**🌍 Country-Based Stem Selection:**
- **albania, armenia, australia, austria, azerbaijan** - Use any country name
- **belgium, croatia, cyprus, czechia, denmark, estonia** - Partial names work too
- **Automatic Key/BPM Matching** - System automatically pitch shifts and time stretches
- **Real-Time Swapping** - Change stems while music is playing
- **Camelot Wheel Compatibility** - Professional harmonic mixing

**🎵 Example Creative Mixes:**
```bash
# Create a Eurovision mega-mix:
swap bass albania             # Albanian bass foundation
swap drums croatia            # Croatian percussion drive  
swap vocals denmark           # Danish vocal melody
swap piano estonia            # Estonian harmonic textures

# Find compatible alternatives:
find bass 8A                  # Find bass stems in key 8A
find drums 130                # Find drums around 130 BPM
```

### 🎛️ **Classic Real-Time Smart Mixer**

**🚀 One-Click Python Mixer:**
```bash
./start_python_mixer.sh
```

**Live Mixing Commands:**
```bash
🎛️🧠 > songs                    # List available songs
🎛️🧠 > a.bass 2                # Load bass from song 2 to deck A
🎛️🧠 > b.vocals.chorus 5       # Load vocals from chorus of song 5 to deck B
🎛️🧠 > bpm 128                 # Set BPM to 128
🎛️🧠 > cross 0.5               # 50/50 crossfade between decks
🎛️🧠 > bass 0.8                # Set bass volume to 80%
🎛️🧠 > random                  # Generate random creative mix
```

### 🎯 **TSP Song Optimization (Standalone)**
```bash
# Analyze all Eurovision songs and find optimal tour
python tsp_autodj.py

# Shows optimal song order considering:
# - Camelot wheel harmonic compatibility  
# - BPM mixing compatibility
# - Energy flow optimization
# - Traveling Salesman Problem solution
```

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

### 🎯 **TSP AutoDJ with Country-Based Stem Swapping**
- **Traveling Salesman Optimization**: Finds mathematically optimal song order through entire Eurovision catalog
- **Camelot Wheel Integration**: Professional harmonic mixing using circle of fifths + major/minor relationships  
- **Country Name Stem Selection**: Use intuitive country names - `albania`, `croatia`, `denmark`, etc.
- **Real-Time Key Adjustment**: Automatic pitch shifting for harmonic compatibility between different countries
- **BPM Synchronization**: Time stretching to match tempos across different Eurovision songs
- **Interactive CLI**: Live stem swapping while music plays - create unique Eurovision mega-mixes
- **Compatibility Finder**: Smart suggestions for stems that work well together
- **Professional Crossfading**: 4-second intelligent crossfades based on harmonic compatibility

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
- **Key Detection**: Eurovision-specific key mapping with Camelot notation
- **Structure Analysis**: Understands song sections and timing
- **Harmonic Mixing**: Professional DJ-style Camelot Wheel compatibility
- **TSP Optimization**: Mathematical approach to optimal song ordering

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

**Option 1: SuperCollider Audio Engine**
- **SuperCollider** 3.12+ (audio server)
- **Python 3.7+** with dependencies:
  - `pythonosc` - OSC communication
  - `pathlib` - File handling
  - `json` - Configuration

**Option 2: Python Audio Engine (Recommended)**
- **Python 3.7+** with dependencies:
  - `pythonosc` - OSC communication
  - `soundfile` - Audio file reading
  - `pyaudio` - Real-time audio playback
  - `numpy` - Audio processing

**Common Requirements:**
- **Audio Files**: WAV format, 44.1kHz stereo preferred
- **Memory**: 16GB+ RAM recommended
- **Song Structures**: JSON metadata files

### 📦 **Installation**

**Option 1: SuperCollider Setup**
```bash
# Install SuperCollider from: https://supercollider.github.io/
# Install Python dependencies:
pip install python-osc pathlib
```

**Option 2: Python Audio Engine Setup (Recommended)**
```bash
# Install Python dependencies:
pip install python-osc soundfile pyaudio numpy
```

## Contributing

The engine is designed to be extensible:
- Add new compatibility algorithms
- Implement additional mixing themes
- Extend key detection systems
- Add support for other audio formats

## License

This project demonstrates advanced music mixing concepts using Eurovision 2025 data for educational and research purposes.
