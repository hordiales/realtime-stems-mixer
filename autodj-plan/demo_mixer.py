#!/usr/bin/env python3
"""
Simple Demo Script for the Eurovision Music Mixing Engine
Shows basic usage and creates example remixes
"""

from advanced_mixer import AdvancedMusicMixer
import json

def create_custom_remix(mixer, base_song_name=None):
    """Create a custom remix with user-friendly interface"""
    
    print("\n🎵 CREATING CUSTOM REMIX 🎵")
    print("=" * 50)
    
    if base_song_name and base_song_name in mixer.songs:
        base_song = mixer.songs[base_song_name]
        print(f"Using base song: {base_song.name}")
        print(f"BPM: {base_song.bpm} | Key: {base_song.key}")
    else:
        print("Available songs:")
        for i, (name, song) in enumerate(mixer.songs.items(), 1):
            short_name = name.split("(")[0].strip()
            print(f"  {i:2d}. {short_name} (BPM: {song.bpm}, Key: {song.key})")
        return None
    
    # Find compatible songs
    compatible = mixer.find_compatible_songs(base_song, base_song.key)
    print(f"\nCompatible songs for mixing ({len(compatible)} found):")
    for song in compatible:
        short_name = song.name.split("(")[0].strip() 
        bpm_diff = abs(song.bpm - base_song.bpm)
        print(f"  - {short_name} (BPM: {song.bpm}, Δ{bpm_diff}, Key: {song.key})")
    
    # Create themed remix
    theme = "energetic" if base_song.bpm > 130 else "chill" if base_song.bpm < 110 else "dramatic"
    print(f"\nAuto-selecting theme: {theme.upper()}")
    
    remix = mixer.create_intelligent_remix(theme)
    
    # Show simplified plan
    print(f"\n📝 REMIX SUMMARY")
    print(f"Theme: {remix['theme'].title()}")
    print(f"Structure: {' → '.join(remix['structure'])}")
    print(f"Base Song: {remix['base_song'].split('(')[0].strip()}")
    print(f"Using {len(remix['compatible_songs'])} compatible songs")
    
    return remix

def save_remix_plan(remix, filename):
    """Save remix plan to JSON file for future use"""
    with open(filename, 'w') as f:
        json.dump(remix, f, indent=2)
    print(f"\n💾 Remix plan saved to: {filename}")

def quick_demo():
    """Run a quick demo of the mixing engine"""
    print("🎼 Eurovision Music Mixing Engine Demo")
    print("=" * 60)
    
    # Initialize mixer
    mixer = AdvancedMusicMixer("stems", "song-structures")
    
    # Show available songs grouped by BPM
    print(f"\n📚 Song Library ({len(mixer.songs)} songs):")
    songs_by_bpm = sorted(mixer.songs.values(), key=lambda s: s.bpm)
    
    current_range = None
    for song in songs_by_bpm:
        bpm_range = f"{(song.bpm//20)*20}-{(song.bpm//20)*20+19}"
        if bpm_range != current_range:
            print(f"\n{bpm_range} BPM:")
            current_range = bpm_range
        
        short_name = song.name.split("(")[0].strip()
        print(f"  {song.bpm:3d} BPM - {short_name:25s} (Key: {song.key})")
    
    # Demo different themes
    themes = ["energetic", "chill", "dramatic"]
    for theme in themes:
        print(f"\n{'='*60}")
        print(f"DEMO: {theme.upper()} REMIX")
        print('='*60)
        
        remix = mixer.create_intelligent_remix(theme)
        
        print(f"\n🎯 {theme.title()} Remix Summary:")
        print(f"Base: {remix['base_song'].split('(')[0].strip()} ({remix['base_bpm']} BPM, {remix['base_key']})")
        print(f"Compatible songs: {len(remix['compatible_songs'])}")
        print(f"Structure: {' → '.join(remix['structure'])}")
        
        # Show some interesting stem combinations
        print(f"\n🎪 Interesting Combinations:")
        section_count = 0
        for section_key, section_data in remix["sections"].items():
            if section_count >= 3:  # Show only first 3 sections
                break
            section_type = section_data["type"]
            
            # Find stems from different songs
            different_songs = set()
            for stem_data in section_data["stems"].values():
                different_songs.add(stem_data["song"].split("(")[0].strip())
            
            if len(different_songs) > 1:
                print(f"  {section_type.title()}: Mixing {len(different_songs)} different songs")
                for stem_type, stem_data in section_data["stems"].items():
                    song_name = stem_data["song"].split("(")[0].strip()
                    if stem_data.get("needs_timestretch", False):
                        print(f"    {stem_type}: {song_name} [time-stretched]")
            section_count += 1
        
        # Save example
        filename = f"remix_{theme}_example.json" 
        save_remix_plan(remix, filename)

def main():
    """Main demo function"""
    try:
        quick_demo()
        
        print(f"\n" + "="*60)
        print("DEMO COMPLETED! 🎉")
        print("="*60)
        print(f"\nYou now have:")
        print(f"  • music_mixer.py - Basic mixing engine")
        print(f"  • advanced_mixer.py - Advanced engine with key detection")
        print(f"  • demo_mixer.py - This demo script")
        print(f"  • 3 example remix JSON files")
        
        print(f"\n💡 Next steps:")
        print(f"  • Implement audio processing to actually mix the stems")
        print(f"  • Add real-time key detection from audio files")  
        print(f"  • Create a web interface for the mixer")
        print(f"  • Add audio effects and transitions")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()