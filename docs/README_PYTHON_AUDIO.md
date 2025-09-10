# Python Audio Server - SuperCollider Replacement

Pure Python implementation of the SuperCollider audio server functionality using PyAudio and soundfile.

## Features

✅ **Same OSC API** - Drop-in replacement for SuperCollider
✅ **Real-time Audio** - Low-latency playback with PyAudio  
✅ **Multi-stem Mixing** - Mix multiple audio stems simultaneously
✅ **Crossfade Control** - Deck A/B crossfading like a DJ mixer
✅ **Rate Control** - Pitch/speed adjustment for each stem
✅ **Memory Efficient** - Dynamic buffer loading and cleanup
✅ **No SuperCollider** - Pure Python, no external dependencies

## Requirements

```bash
pip install numpy soundfile pyaudio python-osc
```

## Usage

### Option 1: Manual Start

1. **Start Audio Server:**
```bash
python audio_server.py
```

2. **Run DJ Plan Executor:**
```bash
python dj_plan_executor.py remix_energetic_example.json
```

### Option 2: Automatic Start

```bash
python run_python_dj.py remix_energetic_example.json
```

## OSC API Compatibility

The Python server implements the exact same OSC messages as SuperCollider:

- `/load_buffer [buffer_id, file_path, stem_name]`
- `/play_stem [buffer_id, rate, volume, loop, start_pos]`
- `/stop_stem [buffer_id]`
- `/stem_volume [buffer_id, volume]`
- `/crossfade_levels [deck_a_vol, deck_b_vol]`
- `/get_status`
- `/test_tone [frequency]`
- `/mixer_cleanup`

## Architecture

### AudioBuffer Class
- Loads audio files using soundfile
- Handles stereo conversion
- Memory usage reporting

### StemPlayer Class  
- Individual playback control
- Rate/pitch adjustment
- Volume control
- Looping support

### PythonAudioServer Class
- Main server coordination
- Real-time audio mixing
- OSC message handling
- PyAudio stream management

## Advantages over SuperCollider

1. **No Errors** - Eliminates SuperCollider timing/race condition errors
2. **Pure Python** - Easier to debug and modify
3. **Better Integration** - Same language as DJ executor
4. **Simpler Setup** - No SuperCollider installation required
5. **Memory Control** - Direct Python memory management

## Performance

- **Sample Rate:** 44.1kHz (matches source files)
- **Chunk Size:** 256 samples (low latency)
- **Channels:** Stereo (2 channels)
- **Format:** 32-bit float

## Testing

```bash
# Test basic server functionality
python test_audio_server.py

# Test with real audio files
python run_python_dj.py remix_dramatic_example.json
```

## Troubleshooting

### Audio Device Issues
```bash
# List available audio devices
python -c "import pyaudio; pa = pyaudio.PyAudio(); [print(f'{i}: {pa.get_device_info_by_index(i)[\"name\"]}') for i in range(pa.get_device_count())]; pa.terminate()"

# Use specific device
python audio_server.py --device 2
```

### Permission Issues (macOS)
- Grant microphone permission if requested
- Check System Preferences > Security & Privacy > Microphone

### Performance Issues
- Close other audio applications
- Reduce system load during playback
- Check audio buffer settings

## Files

- `audio_server.py` - Main audio server implementation
- `run_python_dj.py` - Combined launcher script
- `test_audio_server.py` - Basic functionality test
- `dj_plan_executor.py` - DJ plan executor (unchanged)
- `remix_*.json` - Example DJ plans

## Future Enhancements

- [ ] VST effects support
- [ ] Advanced EQ controls  
- [ ] Recording functionality
- [ ] Multiple output routing
- [ ] MIDI controller integration