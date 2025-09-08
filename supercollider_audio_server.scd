// SuperCollider Audio Server for Eurovision Stem Mixer
// Receives OSC messages from supercollider_stem_mixer.py

(
// Server configuration
s.options.numOutputBusChannels = 2;
s.options.numInputBusChannels = 0;
s.options.sampleRate = 48000;  // Match mixer config
s.options.blockSize = 512;     // Match mixer config
s.options.memSize = 2.pow(20); // 1GB memory

// Boot server
s.waitForBoot {
    
    // Buffers dictionary to store loaded audio
    ~buffers = Dictionary.new;
    
    // Synth definitions for stem playback
    SynthDef(\stemPlayer, {
        arg bufnum = 0, rate = 1.0, vol = 0.8, loop = 1, startPos = 0,
            out = 0, gate = 1, pan = 0;
        
        var sig, env;
        
        // Envelope for smooth start/stop
        env = EnvGen.kr(Env.asr(0.01, 1, 0.1), gate, doneAction: 2);
        
        // PlayBuf with rate control for BPM changes
        sig = PlayBuf.ar(
            numChannels: 2,
            bufnum: bufnum,
            rate: rate * BufRateScale.kr(bufnum),
            startPos: startPos * BufFrames.kr(bufnum),
            loop: loop
        );
        
        // Apply volume and envelope
        sig = sig * vol * env;
        
        // Pan and output
        sig = Balance2.ar(sig[0], sig[1], pan);
        Out.ar(out, sig);
    }).add;
    
    // Master mixer synth
    SynthDef(\masterMixer, {
        arg deckAVol = 0.5, deckBVol = 0.5, masterVol = 0.8,
            deckABus = 10, deckBBus = 12, out = 0;
        
        var deckA, deckB, mix;
        
        // Get audio from deck busses
        deckA = In.ar(deckABus, 2) * deckAVol;
        deckB = In.ar(deckBBus, 2) * deckBVol;
        
        // Mix decks with crossfade
        mix = (deckA + deckB) * masterVol;
        
        // Soft limiting to prevent clipping
        mix = tanh(mix * 2) * 0.5;
        
        Out.ar(out, mix);
    }).add;
    
    // Stem volume control buses
    ~stemBuses = Dictionary.newFrom([
        \bass, Bus.control(s, 1),
        \drums, Bus.control(s, 1),
        \vocals, Bus.control(s, 1),
        \piano, Bus.control(s, 1),
        \other, Bus.control(s, 1)
    ]);
    
    // Initialize stem volume buses
    ~stemBuses.keysValuesDo { |stem, bus|
        bus.set(0.8);
    };
    
    // Audio buses for deck routing
    ~deckABus = Bus.audio(s, 2);
    ~deckBBus = Bus.audio(s, 2);
    
    // Active synths dictionary
    ~activeSynths = Dictionary.new;
    
    // Master mixer instance
    ~masterMixer = Synth(\masterMixer, [
        \deckABus, ~deckABus,
        \deckBBus, ~deckBBus,
        \masterVol, 0.8
    ]);
    
    // Crossfade levels
    ~crossfadePos = 0.0; // 0.0 = full A, 1.0 = full B
    
    s.sync;
    
    // OSC Responder functions
    
    // Load buffer
    OSCdef(\loadBuffer, { |msg, time, addr, port|
        var bufferID = msg[1];
        var filePath = msg[2];
        var stemName = msg[3];
        
        // Load buffer
        ~buffers[bufferID] = Buffer.read(s, filePath, action: { |buf|
            "Loaded buffer % (%) - % frames, % channels".format(
                bufferID, stemName, buf.numFrames, buf.numChannels
            ).postln;
        });
        
    }, '/load_buffer');
    
    // Play stem
    OSCdef(\playStem, { |msg, time, addr, port|
        var bufferID = msg[1];
        var playbackRate = msg[2];
        var volume = msg[3];
        var loop = msg[4];
        var startPos = msg[5];
        var buffer = ~buffers[bufferID];
        var outputBus;
        
        if (buffer.notNil) {
            // Stop existing synth for this buffer
            if (~activeSynths[bufferID].notNil) {
                ~activeSynths[bufferID].set(\gate, 0);
            };
            
            // Determine output bus (deck A or B based on buffer ID range)
            outputBus = if (bufferID < 1100) { ~deckABus } { ~deckBBus };
            
            // Create and play synth
            ~activeSynths[bufferID] = Synth(\stemPlayer, [
                \bufnum, buffer,
                \rate, playbackRate,
                \vol, volume,
                \loop, loop,
                \startPos, startPos,
                \out, outputBus
            ]);
            
            "Playing stem % - rate: %, vol: %".format(
                bufferID, playbackRate, volume
            ).postln;
        } {
            "Buffer % not found".format(bufferID).warn;
        };
        
    }, '/play_stem');
    
    // Stop stem
    OSCdef(\stopStem, { |msg, time, addr, port|
        var bufferID = msg[1];
        
        if (~activeSynths[bufferID].notNil) {
            ~activeSynths[bufferID].set(\gate, 0);
            ~activeSynths[bufferID] = nil;
            "Stopped stem %".format(bufferID).postln;
        };
        
    }, '/stop_stem');
    
    // Stem volume control
    OSCdef(\stemVolume, { |msg, time, addr, port|
        var bufferID = msg[1];
        var volume = msg[2];
        
        if (~activeSynths[bufferID].notNil) {
            ~activeSynths[bufferID].set(\vol, volume);
            "Set stem % volume to %".format(bufferID, volume).postln;
        };
        
    }, '/stem_volume');
    
    // Crossfade levels
    OSCdef(\crossfadeLevels, { |msg, time, addr, port|
        var deckALevel = msg[1];
        var deckBLevel = msg[2];
        
        ~crossfadePos = deckBLevel / (deckALevel + deckBLevel + 0.001);
        
        ~masterMixer.set(
            \deckAVol, deckALevel,
            \deckBVol, deckBLevel
        );
        
        "Crossfade - Deck A: %, Deck B: %".format(
            deckALevel.round(0.01), deckBLevel.round(0.01)
        ).postln;
        
    }, '/crossfade_levels');
    
    // Key change (for future pitch shifting implementation)
    OSCdef(\setKey, { |msg, time, addr, port|
        var key = msg[1];
        "Key change to: %".format(key).postln;
        // TODO: Implement pitch shifting based on key
        
    }, '/set_key');
    
    // Mixer initialization
    OSCdef(\mixerInit, { |msg, time, addr, port|
        var sampleRate = msg[1];
        var numSongs = msg[2];
        
        "Eurovision Mixer initialized - SR: %, Songs: %".format(
            sampleRate, numSongs
        ).postln;
        
    }, '/mixer_init');
    
    // Cleanup
    OSCdef(\mixerCleanup, { |msg, time, addr, port|
        "Cleaning up Eurovision Mixer...".postln;
        
        // Stop all active synths
        ~activeSynths.keysValuesDo { |id, synth|
            if (synth.notNil) { synth.set(\gate, 0) };
        };
        ~activeSynths.clear;
        
        // Free all buffers
        ~buffers.keysValuesDo { |id, buffer|
            buffer.free;
        };
        ~buffers.clear;
        
    }, '/mixer_cleanup');
    
    // Status reporting
    OSCdef(\getStatus, { |msg, time, addr, port|
        "=== SUPERCOLLIDER AUDIO SERVER STATUS ===".postln;
        "Active synths: %".format(~activeSynths.size).postln;
        "Loaded buffers: %".format(~buffers.size).postln;
        "Crossfade position: %".format(~crossfadePos.round(0.01)).postln;
        "Server CPU: %%".format(s.peakCPU.round(0.1)).postln;
        "==========================================".postln;
        
    }, '/get_status');
    
    // Test tone generation
    OSCdef(\testTone, { |msg, time, addr, port|
        var freq = msg[1] ? 440;
        var dur = msg[2] ? 1.0;
        
        {
            var sig = SinOsc.ar(freq, 0, 0.3) * EnvGen.kr(Env.perc(0.01, dur), doneAction: 2);
            Out.ar(0, sig ! 2);
        }.play;
        
        "Test tone: % Hz for % seconds".format(freq, dur).postln;
        
    }, '/test_tone');
    
    "🎛️🔥 SUPERCOLLIDER EUROVISION AUDIO SERVER READY 🔥🎛️".postln;
    "Sample Rate: % Hz".format(s.sampleRate).postln;
    "Block Size: % samples".format(s.options.blockSize).postln;
    "Listening for OSC on port 57120".postln;
    "".postln;
    "Available OSC commands:".postln;
    "/load_buffer [bufferID] [filePath] [stemName]".postln;
    "/play_stem [bufferID] [rate] [volume] [loop] [startPos]".postln;
    "/stop_stem [bufferID]".postln;
    "/stem_volume [bufferID] [volume]".postln;
    "/crossfade_levels [deckALevel] [deckBLevel]".postln;
    "/set_key [key]".postln;
    "/test_tone [frequency] [duration]".postln;
    "/get_status".postln;
    "".postln;
};
)

/*
Usage Instructions:

1. First run this SuperCollider code to start the audio server

2. Then run the Python mixer:
   python supercollider_stem_mixer.py

3. The Python mixer will send OSC messages to SuperCollider for audio playback

OSC Message Flow:
- Python loads stems and sends /load_buffer messages
- Python controls playback with /play_stem messages  
- Python controls mixing with /crossfade_levels messages
- SuperCollider handles all audio processing and output

Test Commands in SuperCollider:
- To test a tone: "/test_tone".sendMsg("localhost", 57120, 440, 2);
- To get status: "/get_status".sendMsg("localhost", 57120);

Benefits of this approach:
- SuperCollider handles all audio I/O (no PyAudio issues)
- Professional audio quality with SuperCollider's DSP
- Real-time parameter control via OSC
- Scalable to complex audio processing
- Cross-platform audio compatibility
*/