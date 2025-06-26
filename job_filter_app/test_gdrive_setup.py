#!/usr/bin/env python3
"""
Test Google Drive Integration Setup
Verifies rclone configuration and Google Drive access
"""

import subprocess
import os
import yaml
from pathlib import Path

def test_rclone_installation():
    """Test if rclone is installed and working"""
    print("🔍 Testing rclone installation...")
    
    try:
        result = subprocess.run(["rclone", "version"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ rclone is installed and working")
            return True
        else:
            print("❌ rclone is not working properly")
            return False
    except FileNotFoundError:
        print("❌ rclone is not installed")
        print("   Install with: curl https://rclone.org/install.sh | sudo bash")
        return False

def test_gdrive_config():
    """Test if Google Drive is configured"""
    print("\n🔍 Testing Google Drive configuration...")
    
    try:
        # Test if gdrive remote exists
        result = subprocess.run(["rclone", "listremotes"], capture_output=True, text=True)
        if result.returncode == 0 and "gdrive:" in result.stdout:
            print("✅ gdrive remote is configured")
            return True
        else:
            print("❌ gdrive remote not found")
            print("   Configure with: rclone config")
            return False
    except Exception as e:
        print(f"❌ Error checking rclone config: {e}")
        return False

def test_gdrive_access():
    """Test if we can access Google Drive"""
    print("\n🔍 Testing Google Drive access...")
    
    try:
        # Test listing Google Drive contents
        result = subprocess.run(["rclone", "lsd", "gdrive:"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Can access Google Drive")
            return True
        else:
            print(f"❌ Cannot access Google Drive: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error accessing Google Drive: {e}")
        return False

def test_ai_jobs_folder():
    """Test if AI-Jobs folder exists and is accessible"""
    print("\n🔍 Testing AI-Jobs folder...")
    
    try:
        # Check if AI-Jobs folder exists
        result = subprocess.run(["rclone", "lsd", "gdrive:AI-Jobs"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ AI-Jobs folder exists and is accessible")
            return True
        else:
            print("⚠️ AI-Jobs folder not found, creating it...")
            # Try to create the folder
            result = subprocess.run(["rclone", "mkdir", "gdrive:AI-Jobs"], capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ AI-Jobs folder created successfully")
                return True
            else:
                print(f"❌ Failed to create AI-Jobs folder: {result.stderr}")
                return False
    except Exception as e:
        print(f"❌ Error testing AI-Jobs folder: {e}")
        return False

def test_upload_download():
    """Test upload and download functionality"""
    print("\n🔍 Testing upload/download functionality...")
    
    try:
        # Create a test file
        test_content = "This is a test file for Google Drive integration"
        test_file = "test_gdrive.txt"
        
        with open(test_file, 'w') as f:
            f.write(test_content)
        
        # Upload test file
        print("📤 Uploading test file...")
        result = subprocess.run(["rclone", "copy", test_file, "gdrive:AI-Jobs/"], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Upload failed: {result.stderr}")
            os.remove(test_file)
            return False
        
        print("✅ Test file uploaded successfully")
        
        # Download test file to verify
        print("📥 Downloading test file for verification...")
        result = subprocess.run(["rclone", "copy", "gdrive:AI-Jobs/test_gdrive.txt", "./"], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Download failed: {result.stderr}")
            os.remove(test_file)
            return False
        
        # Verify content
        with open("test_gdrive.txt", 'r') as f:
            downloaded_content = f.read()
        
        if downloaded_content == test_content:
            print("✅ Upload/download test passed")
            success = True
        else:
            print("❌ Content verification failed")
            success = False
        
        # Cleanup
        os.remove(test_file)
        subprocess.run(["rclone", "delete", "gdrive:AI-Jobs/test_gdrive.txt"], capture_output=True)
        
        return success
        
    except Exception as e:
        print(f"❌ Error in upload/download test: {e}")
        return False

def load_config():
    """Load configuration file"""
    print("\n🔍 Loading configuration...")
    
    config_file = Path("config_scraper.yaml")
    if not config_file.exists():
        print("❌ config_scraper.yaml not found")
        return None
    
    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        print("✅ Configuration loaded successfully")
        return config
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return None

def main():
    """Main test function"""
    print("🧪 Google Drive Integration Test")
    print("=" * 50)
    
    tests = [
        ("Rclone Installation", test_rclone_installation),
        ("Google Drive Config", test_gdrive_config),
        ("Google Drive Access", test_gdrive_access),
        ("AI-Jobs Folder", test_ai_jobs_folder),
        ("Upload/Download", test_upload_download),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
    
    # Load config
    config = load_config()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All tests passed! Google Drive integration is ready.")
        print("\n📝 Next steps:")
        print("1. Run: python scraper_with_git.py")
        print("2. Check Google Drive AI-Jobs folder for uploaded files")
        print("3. Open Colab notebook and mount Google Drive")
        print("4. Load files from AI-Jobs folder")
        
        if config:
            print(f"\n📋 Configuration:")
            print(f"  Google Drive folder: {config.get('gdrive_folder', 'gdrive:AI-Jobs')}")
            print(f"  Upload to Drive: {config.get('upload_to_gdrive', True)}")
    else:
        print("\n⚠️ Some tests failed. Please fix the issues above.")
        print("\n💡 Common fixes:")
        print("1. Install rclone: curl https://rclone.org/install.sh | sudo bash")
        print("2. Configure Google Drive: rclone config")
        print("3. Create AI-Jobs folder: rclone mkdir gdrive:AI-Jobs")
    
    return passed == len(results)

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 