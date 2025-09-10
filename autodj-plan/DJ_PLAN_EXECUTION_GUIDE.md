# 🎧 DJ Plan Execution Guide

Execute remix plans created by `demo_mixer.py` in real-time with SuperCollider audio server like a professional DJ.

## 🚀 Quick Start

### 1. Generate Remix Plans

```bash
python demo_mixer.py
```

This creates three example JSON plans:
- `remix_energetic_example.json` - High-energy mix
- `remix_chill_example.json` - Relaxed, smooth mix  
- `remix_dramatic_example.json` - Dynamic contrast mix

### 2. Start SuperCollider Server

```supercollider
// In SuperCollider IDE:
s.quit; s.reboot;
"supercollider_audio_server_minimal.scd".loadRelative;
```

### 3. Execute DJ Plan

```bash
python dj_plan_executor.py remix_energetic_example.json
```

## 🎛️ Execution Modes

### Interactive Mode (Default)

```bash
python dj_plan_executor.py remix_energetic_example.json
```

**Available commands:**
- `info` - Show detailed plan information
- `list` - List all sections in the plan
- `play <section>` - Play specific section
- `full` - Execute entire plan automatically
- `stop` - Stop all audio
- `quit` - Exit

**Example session:**
```bash
🎛️📄 > info        # Show plan details
🎛️📄 > list        # Show sections
🎛️📄 > play 1      # Play first section
🎛️📄 > play intro  # Play intro section
🎛️📄 > full        # Play entire plan
```

### Full Auto-Play Mode

```bash
python dj_plan_executor.py remix_energetic_example.json --mode full
```

Plays the entire remix automatically with 15-second sections.

### Info Mode

```bash
python dj_plan_executor.py remix_energetic_example.json --mode info
```

Shows detailed plan information without playing.

## 📊 JSON Plan Structure

### Plan Overview
```json
{
  "theme": "energetic",
  "base_song": "01-10 Hallucination (Eurovision 2025 - Denmark)",
  "base_bpm": 140,
  "base_key": "D",
  "structure": ["intro", "verse", "chorus", "verse", "bridge", "chorus", "outro"]
}
```

### Section Details
```json
{
  "sections": {
    "00_intro": {
      "type": "intro",
      "stems": {
        "bass": {
          "song": "01-08 Shh (Eurovision 2025 - Cyprus)",
          "file": "stems/01-08 Shh (Eurovision 2025 - Cyprus)/bass.wav",
          "bpm": 143,
          "key": "A", 
          "pitch_shift": 0.979,
          "needs_timestretch": false
        }
      }
    }
  }
}
```

## 🎵 Example Executions

### Energetic Theme Example

```bash
python dj_plan_executor.py remix_energetic_example.json
```

**Plan Details:**
- **Theme:** ENERGETIC  
- **Base:** Hallucination (140 BPM, Key D)
- **Structure:** intro → verse → chorus → verse → bridge → chorus → chorus → outro
- **Sections:** 8 sections with multi-song stem combinations

**Interactive execution:**
```bash
🎛️📄 > info
📄 REMIX PLAN DETAILS
Theme: ENERGETIC
Base Song: 01-10 Hallucination (Eurovision 2025 - Denmark)
Base BPM: 140
Base Key: D

Structure (8 sections):
   1. intro
   2. verse
   3. chorus
   4. verse
   5. bridge
   6. chorus
   7. chorus
   8. outro

🎛️📄 > play 1
🎵 PLAYING SECTION: 00_INTRO (intro)
📥 Loading: Shh_bass → buffer 1000
📥 Loading: Shh_drums → buffer 1001
▶️  Playing: Shh (rate: 0.979)
▶️  Playing: Shh (rate: 0.979)
✅ Section started with 4 stems
```

### Chill Theme Example

```bash
python dj_plan_executor.py remix_chill_example.json --mode full
```

**Features:**
- Smooth, consistent BPM flow
- Relaxed stem combinations
- Automatic section progression
- 15-second sections with crossfades

### Dramatic Theme Example

```bash
python dj_plan_executor.py remix_dramatic_example.json
```

**Features:**
- Dynamic contrasts between sections
- High/low energy combinations  
- Multiple compatible songs per section
- Creative stem mixing

## 🎛️ Advanced Usage

### Custom SuperCollider Connection

```bash
python dj_plan_executor.py remix_energetic_example.json \
    --host 192.168.1.100 --port 57120
```

### Section-by-Section Control

```bash
# Interactive mode for precise control
python dj_plan_executor.py remix_dramatic_example.json

🎛️📄 > list
📋 Available sections:
   1. 00_verse (verse, 3 stems)
   2. 01_verse (verse, 3 stems)  
   3. 02_chorus (chorus, 3 stems)
   4. 03_bridge (bridge, 3 stems)

🎛️📄 > play verse     # Play first verse section
🎛️📄 > play 3         # Play chorus section
🎛️📄 > stop           # Stop all audio
🎛️📄 > play bridge    # Play bridge section
```

### Performance Workflow

```bash
# 1. Prepare remix plan
python demo_mixer.py

# 2. Review plan details  
python dj_plan_executor.py remix_energetic_example.json --mode info

# 3. Practice with interactive mode
python dj_plan_executor.py remix_energetic_example.json

# 4. Live performance with full auto-play
python dj_plan_executor.py remix_energetic_example.json --mode full
```

## 🔧 Technical Details

### Automatic BPM Matching

The executor automatically applies the `pitch_shift` values from the JSON plan:
- **Rate Calculation:** `target_bpm / source_bpm`
- **Example:** 140 BPM target ÷ 143 BPM source = 0.979 rate
- **Real-time:** Applied during SuperCollider playback

### Buffer Management

- **Smart Loading:** Only loads stems when played
- **Automatic Cleanup:** Previous buffers freed when new sections play
- **Memory Efficient:** Perfect for 16GB systems

### Section Timing

- **Default Duration:** 15 seconds per section
- **Auto-Advance:** Automatically moves to next section in full mode
- **Manual Control:** Interactive mode allows custom timing

## 🎯 Performance Tips

### Pre-Performance Setup

1. **Test Connection:**
   ```bash
   python dj_plan_executor.py remix_energetic_example.json --mode info
   ```

2. **Practice Sections:**
   ```bash
   🎛️📄 > play intro
   🎛️📄 > play chorus  
   🎛️📄 > play bridge
   ```

3. **Check Audio Quality:**
   - Ensure SuperCollider server is running at 44.1kHz
   - Verify all stem files are accessible
   - Test volume levels and crossfades

### Live Execution

- **Interactive Mode:** For DJ-style control with manual section triggers
- **Full Mode:** For automated playback during presentations
- **Stop Command:** Always available for emergency audio cut

### Troubleshooting

**No Audio:**
```bash
🎛️📄 > stop    # Clear all audio
# Check SuperCollider server is running
# Restart server if needed
```

**File Not Found:**
- Ensure stem files exist in the paths specified in JSON
- Check file permissions and absolute paths

**Wrong BPM:**
- JSON plans include automatic pitch_shift calculations  
- No manual BPM adjustment needed

This system turns intelligent remix plans into **live audio performances**! 🎵🎭