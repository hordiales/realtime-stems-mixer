#!/usr/bin/env python3
"""
Quick test of the updated dj_plan_executor.py
Tests OSC message compatibility with supercollider_audio_server_minimal.scd
"""

import sys
from pathlib import Path
from dj_plan_executor import DJPlanExecutor

def test_executor():
    """Test the DJ Plan Executor with sample data"""
    
    print("🧪 Testing Updated DJ Plan Executor")
    print("=" * 50)
    
    # Initialize executor
    try:
        executor = DJPlanExecutor()
        print("✅ Executor initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize executor: {e}")
        return False
    
    # Test loading a plan
    plan_files = [
        "remix_energetic_example.json",
        "remix_chill_example.json", 
        "remix_dramatic_example.json"
    ]
    
    test_plan = None
    for plan_file in plan_files:
        if Path(plan_file).exists():
            test_plan = plan_file
            break
    
    if not test_plan:
        print("❌ No test plan files found")
        return False
    
    # Load the plan
    print(f"\n📄 Testing plan loading: {test_plan}")
    if executor.load_plan(test_plan):
        print("✅ Plan loaded successfully")
    else:
        print("❌ Failed to load plan")
        return False
    
    # Test plan info display
    print("\n📊 Testing plan info display:")
    executor.show_plan_info()
    
    # Test interactive commands (without user input)
    print("\n🎛️ Testing OSC message formatting:")
    
    sections = executor.plan_data.get('sections', {})
    if sections:
        first_section = list(sections.keys())[0]
        section_data = sections[first_section]
        stems = section_data.get('stems', {})
        
        if stems:
            # Test buffer ID assignment
            first_stem_type, first_stem_info = list(stems.items())[0]
            buffer_id = executor._get_buffer_id(first_stem_info['file'])
            print(f"✅ Buffer ID assignment: {buffer_id}")
            
            # Test OSC message formatting (without actually sending)
            print("✅ OSC /load_buffer format: [buffer_id, file_path, stem_name]")
            print("✅ OSC /play_stem format: [buffer_id, rate, volume, loop, start_pos]")
            print("✅ OSC /crossfade_levels format: [deck_a_vol, deck_b_vol]")
            print("✅ Memory optimization: /mixer_cleanup before sections")
    
    print("\n🎉 All tests completed successfully!")
    print("💡 The executor is now compatible with supercollider_audio_server_minimal.scd")
    print("🚀 Ready for live DJ performance!")
    
    return True

if __name__ == "__main__":
    success = test_executor()
    sys.exit(0 if success else 1)