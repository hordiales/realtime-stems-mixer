#!/usr/bin/env python3
"""
Interactive TSP Mixer Demo
Simple demo showing how to use the interactive stem mixer
"""

from interactive_tsp_mixer import InteractiveTSPMixer
import sys
import time

def demo_commands():
    """Show demo of available commands"""
    print("\n🎮 INTERACTIVE MIXER DEMO COMMANDS:")
    print("=" * 50)
    print()
    print("🎵 BASIC USAGE:")
    print("1. Type 'play' to start playback")
    print("2. Type 'status' to see what's playing")
    print("3. Type 'list songs' to see all available songs")
    print()
    print("🔄 STEM SWAPPING EXAMPLES:")
    print("• swap bass albania        - Use bass from Albania")
    print("• swap drums croatia       - Use drums from Croatia")  
    print("• swap vocals denmark      - Use vocals from Denmark")
    print("• swap piano estonia       - Use piano from Estonia")
    print("• swap other australia     - Use 'other' from Australia")
    print()
    print("🔍 FINDING COMPATIBLE STEMS:")
    print("• find bass 4A 120         - Find bass in key 4A around 120 BPM")
    print("• find drums               - Find drums compatible with current song")
    print("• find vocals 8B           - Find vocals in key 8B")
    print()
    print("🔊 VOLUME CONTROL:")
    print("• volume bass 0.5          - Set bass volume to 50%")
    print("• volume drums 1.5         - Set drums volume to 150%")
    print("• mute vocals              - Mute vocals")
    print("• unmute vocals            - Unmute vocals")
    print()
    print("📊 INFO COMMANDS:")
    print("• status                   - Show current mixer status")
    print("• list bass                - List all available bass stems")
    print("• list drums               - List all available drum stems")
    print("• help                     - Show all commands")
    print()
    print("🚪 EXIT:")
    print("• quit or q                - Exit the mixer")
    print()

def main():
    """Main demo function"""
    print("🎯 Interactive TSP Mixer Demo")
    print("=" * 40)
    print("Real-time stem swapping with key/BPM adjustment")
    print("Powered by Traveling Salesman Problem optimization")
    print()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        demo_commands()
        print("To start the interactive mixer:")
        print(f"  python {sys.argv[0]}")
        return
    
    print("🔧 Initializing mixer...")
    mixer = InteractiveTSPMixer()
    
    # Show demo commands before starting
    demo_commands()
    
    print("🚀 Starting interactive session...")
    print("💡 Try these commands to get started:")
    print("   play          - Start playback")
    print("   swap bass albania - Replace bass with Albania's bass")
    print("   status        - See what's currently playing")
    print("   help          - Full command list")
    print()
    
    try:
        # Start the interactive session
        mixer.start_interactive_session()
    except KeyboardInterrupt:
        print("\n👋 Demo ended. Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure you have the required audio files in the 'stems' directory.")

if __name__ == "__main__":
    main()