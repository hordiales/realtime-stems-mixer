# 🧠 Smart Loading Stem Mixer Guide

## Overview

The Smart Loading Stem Mixer (`stem_mixer_smart.py`) is an intelligent real-time audio mixing system designed for Eurovision song stems. It uses **smart loading** to only load audio stems when they're actually playing, making it perfect for systems with memory constraints (like your 16GB system).

## 🚀 Quick Start

### 1. Start Audio Server

**Option A: SuperCollider Audio Server**
```supercollider
// In SuperCollider IDE
"supercollider_audio_server_minimal.scd".loadRelative;
```
Wait for this message: `✅ Server booted successfully with minimal memory!`

**Option B: Python Audio Server (Recommended)**
```bash
# Start Python audio server (no SuperCollider required)
python audio_server.py
```
Wait for: `🎛️💾 PYTHON AUDIO SERVER READY 💾🎛️`

### 2. Run the Smart Mixer

```bash
python stem_mixer_smart.py
```

## 🎛️ Command Interface

### Basic Controls

| Command | Description | Example |
|---------|-------------|---------|
| `bpm <value>` | Set global BPM (60-200) | `bpm 128` |
| `cross <0-1>` | Crossfade between decks | `cross 0.5` |
| `songs` | List all available songs | `songs` |
| `status` | Show mixer status | `status` |
| `memory` | Request SuperCollider memory status | `memory` |
| `cleanup` | Free unused memory | `cleanup` |
| `quit` | Exit mixer | `quit` |

### Smart Stem Loading (Beat-Quantized)

The key feature is **individual stem loading** from different songs with **temporal synchronization**:

| Command | Description | Example |
|---------|-------------|---------|
| `a.<stem> <song>` | Load stem to Deck A (quantized to beat) | `a.bass 2` |
| `b.<stem> <song>` | Load stem to Deck B (quantized to beat) | `b.vocals 5` |
| `a.<stem>.<section> <song>` | Load stem from specific section | `a.drums.chorus 3` |
| `b.<stem>.<section> <song>` | Load stem from specific section | `b.bass.verse 1` |

**Available stems:** `bass`, `drums`, `vocals`, `piano`, `other`

### Instant Playback (No Quantization)

For manual timing control and samples:

| Command | Description | Example |
|---------|-------------|---------|
| `instant.<stem> <song>` | Play stem immediately (no quantization) | `instant.bass 3` |
| `sample.<stem> <song>` | Fire one-shot sample (no loop, instant) | `sample.vocals 1` |

### Temporal Synchronization Controls

| Command | Description | Example |
|---------|-------------|---------|
| `sync on/off` | Enable/disable beat quantization | `sync on` |
| `quantize <1\|2\|4\|8>` | Set quantization resolution (beats) | `quantize 4` |
| `sync status` | Show synchronization status | `sync status` |

### Volume Controls

| Command | Description | Example |
|---------|-------------|---------|
| `bass <0-1>` | Set bass volume across both decks | `bass 0.8` |
| `drums <0-1>` | Set drums volume | `drums 0.6` |
| `vocals <0-1>` | Set vocals volume | `vocals 0.9` |
| `piano <0-1>` | Set piano volume | `piano 0.4` |
| `other <0-1>` | Set other instruments volume | `other 0.5` |

### Advanced Features

| Command | Description | Example |
|---------|-------------|---------|
| `random` | Create random smart mix | `random` |
| `sections <song>` | Show sections for song | `sections 2` |

## 🎵 Song Management

### List Songs

```
🎛️🧠 > songs

🎵 Available Songs (8):
  0: Sweden Loreen Tattoo (BPM: 130, 12 sections)
  1: Finland Kaarija Cha Cha Cha (BPM: 135, 8 sections)
  2: Ukraine Tvorchi Heart Of Steel (BPM: 120, 10 sections)
  3: Spain Blanca Paloma Eaea (BPM: 95, 9 sections)
  ...
```

### View Song Sections

```
🎛️🧠 > sections 0

📊 Sections for Sweden Loreen Tattoo:
  intro: 0.0s - 8.2s
  verse1: 8.2s - 24.1s
  pre-chorus1: 24.1s - 32.3s
  chorus1: 32.3s - 48.2s
  verse2: 48.2s - 64.1s
  ...
```

## 🎛️ Example Mixing Session

### 1. Create a Synchronized Mix

Load different stems from different songs with beat quantization:

```bash
# Check sync status
🎛️🧠 > sync status
🔄 Sync: enabled
⏱️  BPM: 128.0
🎯 Quantize: 1 beats
📍 Current beat: 5.23

# Load bass from song 0 (will wait for next beat)
🎛️🧠 > a.bass 0
📥 Smart loading: bass from Sweden Loreen Tattoo → buffer 1000
⏱️  Quantizing: buffer 1000 in 0.232s
▶️  Smart playing: buffer 1000 (rate: 0.98) 🔄

# Load drums from song 2 (also quantized)
🎛️🧠 > a.drums 2  
📥 Smart loading: drums from Ukraine Tvorchi Heart Of Steel → buffer 1001
⏱️  Quantizing: buffer 1001 in 0.127s
▶️  Smart playing: buffer 1001 (rate: 1.07) 🔄
```

### 1a. Instant Playback (No Sync)

For immediate playback without waiting:

```bash
# Fire instant sample (no sync wait)
🎛️🧠 > sample.vocals 3
📥 Smart loading: vocals from Finland Kaarija Cha Cha Cha → buffer 1002
🎯 Sample fired: vocals from Finland Kaarija Cha Cha Cha

# Play stem instantly (manual timing)
🎛️🧠 > instant.piano 1
📥 Smart loading: piano from Spain Blanca Paloma Eaea → buffer 1003
▶️  Smart playing: buffer 1003 (rate: 1.35) ⏩
```

### 2. Load Specific Sections

```bash
# Load vocals from chorus of song 1
🎛️🧠 > b.vocals.chorus 1
📥 Smart loading: vocals_chorus from Finland Kaarija Cha Cha Cha → buffer 1002
▶️  Smart playing: buffer 1002 from 32.3s [chorus] (rate: 0.93)
```

### 3. Adjust Mix

```bash
# Set volumes
🎛️🧠 > bass 0.7
🔊 Bass volume: 0.70

🎛️🧠 > vocals 0.9
🔊 Vocals volume: 0.90

# Crossfade between decks
🎛️🧠 > cross 0.3
🎚️  Crossfade: 0.30
```

### 4. Change BPM

```bash
🎛️🧠 > bpm 140
🎵 BPM: 140.0
▶️  Smart playing: buffer 1000 (rate: 1.08)  # Automatically adjusts
```

## ⏱️ Temporal Synchronization

### How Beat Quantization Works

The Smart Stem Mixer features **temporal synchronization** to keep all stems perfectly aligned:

1. **Master Timeline:** A global beat timeline runs continuously based on current BPM
2. **Beat Quantization:** New stems wait for the next beat boundary before starting
3. **Instant Override:** Use `instant.*` and `sample.*` commands to bypass quantization
4. **Configurable Resolution:** Set quantization to 1, 2, 4, or 8 beats

### Synchronization Modes

| Mode | Description | When to Use |
|------|-------------|-------------|
| **Quantized** (default) | Waits for next beat boundary | Normal mixing, maintaining rhythm |
| **Instant** | Plays immediately | Manual timing, special effects |
| **Sample** | One-shot, no loop, instant | Sound effects, vocal stabs |

### Sync Controls Examples

```bash
# Enable tight 1-beat quantization
🎛️🧠 > sync on
🔄 Beat quantization enabled

🎛️🧠 > quantize 1
🎯 Quantization set to 1 beats

# Set looser 4-beat quantization (phrase-level)
🎛️🧠 > quantize 4
🎯 Quantization set to 4 beats

# Disable sync for free-form mixing
🎛️🧠 > sync off
⏩ Beat quantization disabled

# Check current sync status
🎛️🧠 > sync status
🔄 Sync: enabled
⏱️  BPM: 140.0
🎯 Quantize: 4 beats
📍 Current beat: 12.75
```

## 💾 Smart Memory Management

### How Smart Loading Works

1. **Only loads when playing:** Audio files are only loaded into SuperCollider when you actually play them
2. **Automatic cleanup:** Old stems are automatically freed when replaced
3. **Memory monitoring:** Use `memory` and `cleanup` commands to monitor usage

### Memory Commands

```bash
# Check memory usage
🎛️🧠 > memory
📊 Requested memory status from SuperCollider

# Manual cleanup (happens automatically)
🎛️🧠 > cleanup  
🧹 Requested memory cleanup from SuperCollider
```

### Status Monitoring

```bash
🎛️🧠 > status

🎛️🧠 SMART LOADING STEM MIXER STATUS
==================================================
🎵 BPM: 140.0
🎚️  Crossfade: 0.30
🔊 Master Volume: 0.80

💾 Memory Status:
  Loaded buffers: 3
  Playing stems: 3

🎵 DECK A:
  bass: Sweden Loreen Tattoo (buffer: 1000)
  drums: Ukraine Tvorchi Heart Of Steel (buffer: 1001)

🎵 DECK B:
  vocals: Finland Kaarija Cha Cha Cha [chorus] (buffer: 1002)
```

## 🎲 Random Mode

Generate instant creative mixes:

```bash
🎛️🧠 > random
🎲 Random smart mix: BPM 127
📥 Smart loading: bass from Spain Blanca Paloma Eaea → buffer 1003
📥 Smart loading: drums_verse from Sweden Loreen Tattoo → buffer 1004
📥 Smart loading: vocals_chorus from Finland Kaarija Cha Cha Cha → buffer 1005
...
```

## 🔧 Configuration

### Mixer Config (`mixer_config.json`)

The smart mixer uses the same configuration as other mixers:

```json
{
  "audio": {
    "sample_rate": 48000,
    "buffer_size": 512,
    "master_volume": 0.8
  },
  "mixing": {
    "stem_volumes": {
      "bass": 0.8,
      "drums": 0.7,
      "vocals": 0.9,
      "piano": 0.6,
      "other": 0.5
    }
  },
  "osc": {
    "enable_osc": true,
    "host": "localhost",
    "port": 5005
  }
}
```

## 📡 OSC Control

External OSC control is available on port 5005:

```python
# Example OSC messages
/bpm 128.0
/crossfade 0.5
/stem/bass 0.8
/random
/status
```

## ⚠️ Troubleshooting

### SuperCollider Won't Boot

```bash
# Try even smaller memory in SuperCollider:
s.options.memSize = 2.pow(16);  // 64MB only
s.reboot;
"supercollider_audio_server_minimal.scd".loadRelative;
```

### Audio Issues

1. **No sound:** Check that SuperCollider server is running
2. **Crackling:** Try increasing SuperCollider's buffer size
3. **Memory errors:** Use `cleanup` command or restart SuperCollider

### Missing Songs

1. Ensure stems are in `stems/` directory
2. Each song needs a subdirectory with stem files: `bass.wav`, `drums.wav`, etc.
3. Song structures should be in `song-structures/` as JSON files

## 🎯 Key Benefits

1. **Memory Efficient:** Only loads what's playing (perfect for 16GB systems)
2. **Individual Stems:** Mix bass from one song with drums from another
3. **Section-Based:** Play specific parts (verse, chorus, bridge, etc.)
4. **Real-time:** Instant BPM and pitch adjustments
5. **Smart Cleanup:** Automatic memory management
6. **Visual Feedback:** Clear status and loading information
7. **Temporal Sync:** Beat-quantized loading keeps everything perfectly aligned
8. **Flexible Timing:** Choose between quantized, instant, or one-shot playback modes
9. **Performance Ready:** Live-friendly sync controls for DJ techniques

## 🚀 Advanced Usage

### Create Complex Synchronized Mixes

```bash
# Progressive house build-up with beat quantization
🎛️🧠 > bpm 128
🎛️🧠 > quantize 4          # 4-beat phrase quantization
🎛️🧠 > a.bass.intro 0      # Quantized to phrase boundary
⏱️  Quantizing: buffer 1000 in 1.250s
🎛️🧠 > a.drums.verse 1     # Will align with bass
⏱️  Quantizing: buffer 1001 in 0.625s
🎛️🧠 > b.vocals.chorus 2   # Prepare vocals on B (quantized)
🎛️🧠 > cross 0.0           # Only A playing
🎛️🧠 > cross 0.5           # Blend in vocals
🎛️🧠 > instant.piano 3     # Add piano immediately (no wait)
▶️  Smart playing: buffer 1003 (rate: 1.07) ⏩
```

### Performance Techniques

```bash
# Quick drop and build technique
🎛️🧠 > sync off           # Disable for instant control
🎛️🧠 > sample.vocals 2    # Drop vocal sample instantly
🎛️🧠 > sync on            # Re-enable for next elements
🎛️🧠 > quantize 1         # Tight timing
🎛️🧠 > a.drums 4          # Drums on next beat
🎛️🧠 > a.bass 4           # Bass on next beat (layered)
```

### Live Performance

```bash
# Quick performance commands
🎛️🧠 > random             # Instant creative mix
🎛️🧠 > bpm 140           # Speed up
🎛️🧠 > vocals 0.0        # Drop vocals
🎛️🧠 > drums 1.0         # Full drums
🎛️🧠 > cross 1.0         # Switch to B deck
```

This smart loading approach gives you maximum creative control while being gentle on your system's memory!