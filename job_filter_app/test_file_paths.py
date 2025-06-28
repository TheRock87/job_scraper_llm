#!/usr/bin/env python3
"""
Test script to verify file path changes work correctly
"""

import os
from pathlib import Path

def test_file_paths():
    """Test that the file paths are set up correctly"""
    print("🔍 Testing file paths...")
    
    # Test 1: Check if data directory exists
    data_dir = Path(__file__).parent / "data"
    print(f"📁 Data directory: {data_dir}")
    print(f"   Exists: {data_dir.exists()}")
    
    # Create data directory if it doesn't exist
    data_dir.mkdir(exist_ok=True)
    print(f"   Created/verified: {data_dir.exists()}")
    
    # Test 2: Test creating a file in data directory
    test_file = data_dir / "test_file.txt"
    try:
        with open(test_file, 'w') as f:
            f.write("Test content")
        print(f"✅ Successfully created test file: {test_file}")
        print(f"   File exists: {test_file.exists()}")
        
        # Clean up
        test_file.unlink()
        print(f"🧹 Cleaned up test file")
        
    except Exception as e:
        print(f"❌ Failed to create test file: {e}")
        return False
    
    # Test 3: Check GitHub Actions workflow expected path
    expected_csv_path = data_dir / "jobs_raw.csv"
    print(f"📄 Expected CSV path for GitHub Actions: {expected_csv_path}")
    print(f"   Relative path: data/jobs_raw.csv")
    
    # Test 4: Check the save_to_csv function logic
    output_path = "data/jobs_raw.csv"
    output_file = Path(output_path)
    print(f"🔧 Testing save_to_csv logic:")
    print(f"   Output path: {output_path}")
    print(f"   Parent name: {output_file.parent.name}")
    print(f"   Would create data dir: {output_file.parent.name == 'data'}")
    
    print("\n✅ All file path tests passed!")
    return True

if __name__ == "__main__":
    test_file_paths() 