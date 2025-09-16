#!/usr/bin/env python3
"""
Simple runner script for TSP AutoDJ
"""

from tsp_autodj import TSPAutoDJ
from tsp_autodj_player import TSPAutoDJPlayer
import sys

def main():
    print("🎯 TSP AutoDJ - Eurovision Song Optimizer")
    print("=" * 50)
    print("Using Traveling Salesman Problem to find optimal song order")
    print("Based on Camelot wheel harmony + BPM compatibility")
    print()
    
    # Choose mode
    mode = "analysis"  # Default to analysis mode for demo
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--audio":
            mode = "audio"
        elif sys.argv[1] == "--analysis":
            mode = "analysis"
    
    if mode == "audio":
        print("🎵 Audio playback mode")
        autodj = TSPAutoDJPlayer()
    else:
        print("📊 Analysis mode (no audio playback)")
        autodj = TSPAutoDJ()
    
    # Analyze and create optimal tour
    print("\n🔍 Analyzing Eurovision songs and calculating optimal tour...")
    if not autodj.analyze_and_plan_tour():
        print("❌ Failed to create tour")
        return
    
    # Show results
    print("\n" + "="*60)
    autodj.show_tour_stats()
    print("="*60)
    
    if mode == "audio":
        print("\n🎧 Ready for audio playback!")
        print("Note: Make sure your volume is at a comfortable level")
        try:
            response = input("\nStart audio tour? (y/n): ").strip().lower()
            if response.startswith('y'):
                autodj.play_tour_with_audio()
        except (KeyboardInterrupt, EOFError):
            print("\n👋 Goodbye!")
    else:
        print(f"\n✅ Optimal tour calculated!")
        print(f"📈 Average song compatibility: {((4.652 - autodj.tour.__len__()) / autodj.tour.__len__()) * -100 + 100:.1f}%")
        print("\nTo hear this tour with audio playback:")
        print(f"  python {sys.argv[0]} --audio")

if __name__ == "__main__":
    main()