# 📡 OSC Messages Reference - Audio Servers

This document describes all OSC messages supported by both audio server options:
- **SuperCollider Minimal Audio Server** (`supercollider_audio_server_minimal.scd`)
- **Python Audio Server** (`audio_server.py`)

## 🎛️ **Server Configuration**

- **Host:** `localhost` (127.0.0.1)
- **Port:** `57120` (SuperCollider default)
- **Protocol:** UDP
- **Sample Rate:** 44.1kHz (optimized for Eurovision stems)
- **Audio Output:** Stereo (channels 0-1)

## 📊 **Buffer and Synth Management**

### Load Audio Buffer

**Message:** `/load_buffer`

**Parameters:**
1. `bufferID` (Integer) - Unique buffer identifier (1000+)
2. `filePath` (String) - Absolute path to audio file
3. `stemName` (String) - Display name for logging

**Example:**
```
/load_buffer 1001 "/path/to/stems/song/bass.wav" "Song_Bass"
```

**Response:**
```
✅ Loaded Song_Bass (8.5 MB)
```

---

### Play Stem

**Message:** `/play_stem`

**Parameters:**
1. `bufferID` (Integer) - Buffer to play
2. `rate` (Float) - Playback rate (1.0 = normal speed)
3. `volume` (Float) - Volume level (0.0 - 1.0)
4. `loop` (Integer) - Loop mode (1 = loop, 0 = no loop)
5. `startPos` (Float) - Start position (0.0 - 1.0)

**Example:**
```
/play_stem 1001 1.2 0.8 1 0.0
```
*Play buffer 1001 at 120% speed, 80% volume, looping from start*

**Bus Assignment:**
- Buffer IDs < 1100: Output to **Deck A** (bus 10-11)
- Buffer IDs >= 1100: Output to **Deck B** (bus 12-13)

---

### Play Stem Section

**Message:** `/play_stem_section`

Same parameters as `/play_stem` - automatically redirected.

**Example:**
```
/play_stem_section 1001 1.0 0.9 1 0.25 2.5
```
*Play from 25% position for 2.5 seconds duration*

---

### Stop Stem

**Message:** `/stop_stem`

**Parameters:**
1. `bufferID` (Integer) - Buffer to stop

**Example:**
```
/stop_stem 1001
```

**Response:**
```
⏹️  Stopped 1001
```

---

### Set Stem Volume

**Message:** `/stem_volume`

**Parameters:**
1. `bufferID` (Integer) - Buffer to adjust
2. `volume` (Float) - New volume level (0.0 - 1.0)

**Example:**
```
/stem_volume 1001 0.6
```

---

## 🎚️ **Mixing Controls**

### Crossfade Between Decks

**Message:** `/crossfade_levels`

**Parameters:**
1. `deckALevel` (Float) - Deck A volume (0.0 - 1.0)
2. `deckBLevel` (Float) - Deck B volume (0.0 - 1.0)

**Example:**
```
/crossfade_levels 0.7 0.3
```
*70% Deck A, 30% Deck B*

**Response:**
```
🎚️  A:0.70 B:0.30
```

---

## 🔧 **System Control**

### Get Server Status

**Message:** `/get_status`

**Parameters:** None

**Example:**
```
/get_status
```

**Response:**
```
=== MINIMAL SUPERCOLLIDER SERVER ===
Memory: 256 MB allocated
Buffers loaded: 3
Active synths: 2
CPU: 12.5%
```

---

### Test Tone

**Message:** `/test_tone`

**Parameters:**
1. `frequency` (Float, Optional) - Frequency in Hz (default: 440)

**Example:**
```
/test_tone 880
```

**Response:**
```
🎵 Tone: 880 Hz
```

---

### Memory Cleanup

**Message:** `/mixer_cleanup`

**Parameters:** None

**Example:**
```
/mixer_cleanup
```

**Response:**
```
🧹 Cleaned
```

*Frees all active synths and buffers*

---

## 🎵 **Usage Examples**

### Basic Stem Loading and Playback

```bash
# Load stems
/load_buffer 1000 "/stems/song1/bass.wav" "Song1_Bass"
/load_buffer 1001 "/stems/song1/drums.wav" "Song1_Drums" 
/load_buffer 1100 "/stems/song2/vocals.wav" "Song2_Vocals"

# Play on different decks
/play_stem 1000 1.0 0.8 1 0.0    # Bass on Deck A
/play_stem 1001 1.1 0.7 1 0.0    # Drums on Deck A (faster)
/play_stem 1100 0.95 0.9 1 0.0   # Vocals on Deck B (slower)

# Mix between decks
/crossfade_levels 1.0 0.0        # Only Deck A
/crossfade_levels 0.5 0.5        # Equal mix
/crossfade_levels 0.0 1.0        # Only Deck B
```

### BPM Matching Example

```bash
# Original BPM: 120, Target BPM: 128
# Rate calculation: 128/120 = 1.067

/load_buffer 1000 "/stems/song/bass.wav" "Bass_120BPM"
/play_stem 1000 1.067 0.8 1 0.0  # Speed up to 128 BPM
```

### Section-Based Playback

```bash
# Play chorus section starting at 45% through the song
/load_buffer 1001 "/stems/song/vocals.wav" "Vocals_Chorus"
/play_stem_section 1001 1.0 0.9 1 0.45
```

### Volume Automation

```bash
# Gradual fade out
/stem_volume 1000 1.0
/stem_volume 1000 0.8    # Step down
/stem_volume 1000 0.6
/stem_volume 1000 0.4
/stem_volume 1000 0.2
/stem_volume 1000 0.0    # Silent
```

### Live Performance Workflow

```bash
# Setup
/get_status                          # Check system

# Load next songs
/load_buffer 1002 "/stems/song3/bass.wav" "Song3_Bass"
/load_buffer 1003 "/stems/song3/drums.wav" "Song3_Drums"

# Quick switch
/stop_stem 1000                      # Stop current bass
/play_stem 1002 1.0 0.8 1 0.0       # Start new bass immediately

# Cleanup when done
/mixer_cleanup                       # Free all resources
```

## 🚀 **Integration with Python Mixer**

The **Smart Stem Mixer** (`stem_mixer_smart.py`) automatically sends these OSC messages based on user commands:

| Mixer Command | OSC Message | Purpose |
|---------------|-------------|---------|
| `a.bass 2` | `/load_buffer` + `/play_stem` | Load bass from song 2 to deck A |
| `cross 0.5` | `/crossfade_levels 0.5 0.5` | 50/50 crossfade |
| `bass 0.8` | `/stem_volume` (all bass buffers) | Set bass volume |
| `status` | `/get_status` | Server status |
| `cleanup` | `/mixer_cleanup` | Memory cleanup |

## 📊 **Error Handling**

### Common Responses

| Message | Meaning |
|---------|---------|
| `✅ Loaded [stem] (X.X MB)` | Buffer loaded successfully |
| `❌ Load failed: [stem]` | File not found or corrupt |
| `▶️  Playing buffer X` | Stem playing successfully |
| `❌ Buffer X not ready` | Buffer not loaded before play |
| `⏹️  Stopped X` | Stem stopped successfully |
| `🧹 Cleaned` | Memory cleanup completed |

### Troubleshooting

1. **Buffer not ready:** Ensure `/load_buffer` completes before `/play_stem`
2. **No sound:** Check `/crossfade_levels` and volume parameters
3. **Memory issues:** Use `/mixer_cleanup` regularly
4. **CPU overload:** Reduce number of simultaneous stems

## 🎛️ **Technical Specifications**

- **Maximum Buffers:** Limited by 256MB memory allocation
- **Audio Quality:** 44.1kHz/16-bit (matches Eurovision stems)
- **Latency:** ~256 samples (5.8ms at 44.1kHz)
- **Deck Assignment:** Buffer ID determines output bus
- **File Formats:** WAV (recommended), other formats via SuperCollider

This OSC protocol enables full remote control of the Eurovision stem mixing system! 🎵✨