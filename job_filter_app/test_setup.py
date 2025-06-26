#!/usr/bin/env python3
"""
Test script to verify the new separated workflow setup
"""

import sys
from pathlib import Path
import yaml

def test_imports():
    """Test that all required modules can be imported"""
    print("🔍 Testing imports...")
    
    try:
        import pandas as pd
        print("✅ pandas imported")
    except ImportError as e:
        print(f"❌ pandas import failed: {e}")
        return False
    
    try:
        import yaml
        print("✅ yaml imported")
    except ImportError as e:
        print(f"❌ yaml import failed: {e}")
        return False
    
    try:
        # Test jobspy import
        current_dir = Path(__file__).resolve().parent
        jobspy_path = current_dir.parent
        sys.path.insert(0, str(jobspy_path))
        
        from jobspy import scrape_jobs
        print("✅ jobspy imported")
    except ImportError as e:
        print(f"❌ jobspy import failed: {e}")
        return False
    
    return True

def test_config():
    """Test configuration files"""
    print("\n🔍 Testing configuration...")
    
    current_dir = Path(__file__).resolve().parent
    
    # Test scraper config
    scraper_config = current_dir / "config_scraper.yaml"
    if scraper_config.exists():
        try:
            with open(scraper_config, 'r') as f:
                config = yaml.safe_load(f)
            
            required_fields = ["search_term", "locations", "site_name", "results_wanted"]
            missing_fields = [field for field in required_fields if field not in config]
            
            if not missing_fields:
                print("✅ config_scraper.yaml is valid")
                return True
            else:
                print(f"❌ Missing fields in config_scraper.yaml: {missing_fields}")
                return False
        except Exception as e:
            print(f"❌ Error reading config_scraper.yaml: {e}")
            return False
    else:
        print("❌ config_scraper.yaml not found")
        return False

def test_scripts():
    """Test that required scripts exist"""
    print("\n🔍 Testing scripts...")
    
    current_dir = Path(__file__).resolve().parent
    required_scripts = ["scraper_only.py", "setup_cron.py"]
    
    for script in required_scripts:
        script_path = current_dir / script
        if script_path.exists():
            print(f"✅ {script} exists")
        else:
            print(f"❌ {script} not found")
            return False
    
    return True

def test_rclone():
    """Test if rclone is available"""
    print("\n🔍 Testing rclone...")
    
    import subprocess
    try:
        result = subprocess.run(["rclone", "version"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ rclone is installed")
            return True
        else:
            print("❌ rclone is not working properly")
            return False
    except FileNotFoundError:
        print("⚠️ rclone is not installed")
        print("   Install with: curl https://rclone.org/install.sh | sudo bash")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing JobSpy Separated Workflow Setup")
    print("=" * 50)
    
    tests = [
        ("Imports", test_imports),
        ("Configuration", test_config),
        ("Scripts", test_scripts),
        ("Rclone", test_rclone),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
    
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
        print("\n🎉 All tests passed! Your setup is ready.")
        print("\n📝 Next steps:")
        print("1. Configure rclone: rclone config")
        print("2. Test scraping: python3 scraper_only.py")
        print("3. Setup automation: python3 setup_cron.py install")
        print("4. Upload job_filtering_colab.ipynb to Google Colab")
    else:
        print("\n⚠️ Some tests failed. Please fix the issues above.")
    
    return passed == len(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 