// MINIMAL Memory SuperCollider Audio Server
// For systems with limited RAM - loads only what's needed

(
// Minimal server configuration - start small
s.options.memSize = 2.pow(18);           // 256MB only (very conservative)
s.options.numBuffers = 128;              // Minimal buffers
s.options.maxNodes = 256;                // Minimal nodes
s.options.numRGens = 32;                 // Minimal RGens
s.options.numWireBufs = 32;              // Minimal wire buffers
s.options.numOutputBusChannels = 2;      // Stereo out only
s.options.numInputBusChannels = 0;       // No inputs needed
s.options.sampleRate = 48000;
s.options.blockSize = 512;

// Show memory info before booting
"Attempting to boot with minimal settings:".postln;
"Memory: % MB".format(s.options.memSize / 1024).postln;
"Buffers: %".format(s.options.numBuffers).postln;

s.waitForBoot({
    
    "✅ Server booted successfully with minimal memory!".postln;
    "Allocated: % MB".format(s.options.memSize / 1024).postln;
    
    // Storage
    ~buffers = Dictionary.new;
    ~activeSynths = Dictionary.new;
    
    // Simple stem player only
    SynthDef(\stemPlayer, {
        arg bufnum = 0, rate = 1.0, vol = 0.8, startPos = 0, out = 0, gate = 1;
        
        var sig, env;
        
        env = EnvGen.kr(Env.asr(0.01, 1, 0.1), gate, doneAction: 2);
        
        // Simple playback - no loop to save memory
        sig = PlayBuf.ar(2, bufnum, rate * BufRateScale.kr(bufnum), 
                         startPos: startPos * BufSampleRate.kr(bufnum), 
                         doneAction: 0);
        
        sig = sig * vol * env;
        Out.ar(out, sig);
    }).add;
    
    // Simple mixer
    SynthDef(\simpleMixer, {
        arg deckAVol = 0.8, deckBVol = 0.0, masterVol = 0.8, out = 0;
        var deckA, deckB, mix;
        
        deckA = In.ar(10, 2) * deckAVol;  // Deck A bus
        deckB = In.ar(12, 2) * deckBVol;  // Deck B bus
        mix = (deckA + deckB) * masterVol;
        mix = tanh(mix);  // Simple limiting
        Out.ar(out, mix);
    }).add;
    
    // Audio buses
    ~deckABus = Bus.audio(s, 2);  // Bus 10-11
    ~deckBBus = Bus.audio(s, 2);  // Bus 12-13
    
    s.sync;
    
    // Start mixer
    ~mixer = Synth(\simpleMixer);
    
    s.sync;
    
    // OSC Responders - minimal version
    
    // Load buffer - free previous to save memory
    OSCdef(\loadBuffer, { |msg|
        var bufferID = msg[1].asInteger;
        var filePath = msg[2].asString;
        var stemName = msg[3].asString;
        
        // Always free old buffer first
        if(~buffers[bufferID].notNil) {
            ~buffers[bufferID].free;
            "Freed buffer %".format(bufferID).postln;
        };
        
        // Load new buffer
        ~buffers[bufferID] = Buffer.read(s, filePath, action: { |buf|
            if(buf.numFrames > 0) {
                var mb = (buf.numFrames * buf.numChannels * 4 / 1048576).round(0.1);
                "✅ Loaded % (%.1f MB)".format(stemName, mb).postln;
            } {
                "❌ Load failed: %".format(stemName).postln;
            };
        });
        
    }, '/load_buffer');
    
    // Play stem - simple version
    OSCdef(\playStem, { |msg|
        var bufferID = msg[1].asInteger;
        var rate = msg[2].asFloat;
        var volume = msg[3].asFloat;
        var loop = msg[4].asInteger;  // Ignored for simplicity
        var startPos = msg[5].asFloat;
        var buffer = ~buffers[bufferID];
        var outputBus;
        
        if(buffer.notNil and: { buffer.numFrames > 0 }) {
            
            // Stop old synth
            if(~activeSynths[bufferID].notNil) {
                ~activeSynths[bufferID].free;
            };
            
            // Choose output bus
            outputBus = if(bufferID < 1100) { 10 } { 12 };
            
            // Play new synth
            ~activeSynths[bufferID] = Synth(\stemPlayer, [
                \bufnum, buffer,
                \rate, rate,
                \vol, volume,
                \startPos, startPos,
                \out, outputBus
            ]);
            
            "▶️  Playing buffer %".format(bufferID).postln;
        } {
            "❌ Buffer % not ready".format(bufferID).postln;
        };
        
    }, '/play_stem');
    
    // Section playback - redirect to regular play
    OSCdef(\playStemSection, { |msg|
        // Use first 6 params only (ignore duration for now)
        var newMsg = msg[0..5];  
        OSCdef(\playStem).func.value(newMsg);
    }, '/play_stem_section');
    
    // Stop stem
    OSCdef(\stopStem, { |msg|
        var bufferID = msg[1].asInteger;
        if(~activeSynths[bufferID].notNil) {
            ~activeSynths[bufferID].free;
            ~activeSynths[bufferID] = nil;
            "⏹️  Stopped %".format(bufferID).postln;
        };
    }, '/stop_stem');
    
    // Volume
    OSCdef(\stemVolume, { |msg|
        var bufferID = msg[1].asInteger;
        var volume = msg[2].asFloat;
        if(~activeSynths[bufferID].notNil) {
            ~activeSynths[bufferID].set(\vol, volume);
        };
    }, '/stem_volume');
    
    // Crossfade
    OSCdef(\crossfadeLevels, { |msg|
        var deckALevel = msg[1].asFloat;
        var deckBLevel = msg[2].asFloat;
        
        ~mixer.set(\deckAVol, deckALevel, \deckBVol, deckBLevel);
        "🎚️  A:% B:%".format(deckALevel.round(0.01), deckBLevel.round(0.01)).postln;
    }, '/crossfade_levels');
    
    // Status
    OSCdef(\getStatus, { |msg|
        "=== MINIMAL SUPERCOLLIDER SERVER ===".postln;
        "Memory: % MB allocated".format(s.options.memSize / 1024).postln;
        "Buffers loaded: %".format(~buffers.size).postln;
        "Active synths: %".format(~activeSynths.size).postln;
        "CPU: %%".format(s.peakCPU.round(0.1)).postln;
    }, '/get_status');
    
    // Test tone
    OSCdef(\testTone, { |msg|
        var freq = msg[1] ? 440;
        { SinOsc.ar(freq, 0, 0.1) ! 2 * EnvGen.kr(Env.perc(0.01, 0.5), doneAction: 2) }.play;
        "🎵 Tone: % Hz".format(freq).postln;
    }, '/test_tone');
    
    // Cleanup
    OSCdef(\mixerCleanup, {
        ~activeSynths.do(_.free); ~activeSynths.clear;
        ~buffers.do(_.free); ~buffers.clear;
        "🧹 Cleaned".postln;
    }, '/mixer_cleanup');
    
    "🎛️💾 MINIMAL SUPERCOLLIDER SERVER READY 💾🎛️".postln;
    "Memory: % MB (very conservative)".format(s.options.memSize / 1024).postln;
    "⚠️  Loads only 1-2 stems at a time to save memory".postln;
    "💡 Use /get_status to monitor memory usage".postln;
    "".postln;
    
}, onFailure: {
    
    "❌ EVEN MINIMAL SETTINGS FAILED!".postln;
    "💡 Your system may be very low on RAM.".postln;
    "Try these steps:".postln;
    "1. Close all other applications".postln;
    "2. Restart SuperCollider completely".postln;
    "3. Try even smaller: s.options.memSize = 2.pow(16); s.reboot;".postln;
    "4. Or use file-based playback instead of real-time".postln;
    
});
)

/*
ULTRA-MINIMAL SUPERCOLLIDER INSTRUCTIONS:

This version uses only 256MB of memory and loads 1-2 stems at a time.

If this STILL fails, try in SuperCollider:
1. s.options.memSize = 2.pow(16);  // 64MB only!
2. s.reboot;
3. Run this file

Or check available memory:
Platform.totalMemory  // Shows system memory
*/