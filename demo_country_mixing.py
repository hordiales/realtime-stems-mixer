#!/usr/bin/env python3
"""
Demo script showing country-based stem mixing in stem_mixer_smart.py
"""

import time
from stem_mixer_smart import SmartSuperColliderStemMixer

def demo_country_commands():
    """Show demo of country-based commands"""
    print("🌍 EUROVISION COUNTRY-BASED STEM MIXING DEMO")
    print("=" * 50)
    print()
    
    # Initialize mixer
    mixer = SmartSuperColliderStemMixer()
    
    print("\n🎯 AVAILABLE EUROVISION COUNTRIES:")
    print("-" * 40)
    countries_seen = set()
    for i, song in enumerate(mixer.available_songs):
        country = song.get('country', 'unknown').title()
        if country not in countries_seen:
            countries_seen.add(country)
            print(f"  {country.lower():<12} - {song['name']} (BPM: {song['bpm']:.0f})")
    
    print(f"\n✅ Total countries: {len(countries_seen)}")
    
    print("\n🎛️  COUNTRY-BASED MIXING COMMANDS:")
    print("=" * 50)
    print("🔄 DECK LOADING (Beat-Quantized):")
    print("  a.bass albania        - Load Albanian bass to deck A")
    print("  b.drums croatia       - Load Croatian drums to deck B")
    print("  a.vocals.chorus denmark - Load Danish vocals (chorus section) to deck A")
    print("  b.piano estonia       - Load Estonian piano to deck B")
    print()
    print("⚡ INSTANT PLAYBACK:")
    print("  instant.bass australia  - Play Australian bass immediately")
    print("  sample.vocals cyprus    - Fire Cypriot vocal sample")
    print()
    print("📊 INFO COMMANDS:")
    print("  songs                  - List all countries and songs")
    print("  sections albania       - Show sections in Albanian song")
    print("  status                 - Show current mix status")
    print()
    print("🔊 VOLUME & MIXING:")
    print("  bass 0.8              - Set bass volume to 80%")
    print("  cross 0.5             - 50/50 crossfade between decks")
    print("  bpm 128               - Set master BPM to 128")
    print()
    
    print("🎵 EXAMPLE EUROVISION MIX SESSION:")
    print("=" * 50)
    print("1. a.bass albania         # Albanian bass foundation")
    print("2. b.drums croatia        # Croatian percussion")
    print("3. cross 0.3              # Mix 30% deck B")
    print("4. a.vocals denmark       # Add Danish vocals to A")
    print("5. b.piano.chorus estonia # Estonian piano chorus on B")
    print("6. instant.other australia # Fire Australian 'other' stem")
    print("7. cross 0.7              # More deck B (Estonian piano)")
    print("8. sample.vocals cyprus   # Add Cypriot vocal sample")
    print()
    
    print("🚀 TO START THE INTERACTIVE MIXER:")
    print("   python stem_mixer_smart.py")
    print()
    print("💡 TIPS:")
    print("  • Use country names OR numbers: 'albania' or '0'")
    print("  • All commands are beat-quantized for perfect timing")
    print("  • Type 'songs' to see all available countries")
    print("  • Type 'help' in the mixer for full command list")
    print()
    
    # Test a few country lookups
    print("🧪 TESTING COUNTRY LOOKUPS:")
    test_countries = ['albania', 'croatia', 'denmark', 'estonia', 'cyprus']
    for country in test_countries:
        idx = mixer._find_song_by_identifier(country)
        if idx is not None:
            song = mixer.available_songs[idx]
            print(f"  ✅ {country:<8} -> {song['name']} (BPM: {song['bpm']:.0f})")
        else:
            print(f"  ❌ {country:<8} -> Not found")
    
    print("\n🎉 Ready to mix Eurovision stems by country!")
    mixer.stop()

if __name__ == "__main__":
    demo_country_commands()