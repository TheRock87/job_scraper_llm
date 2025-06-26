#!/usr/bin/env python3
"""
Setup cron job for automatic job scraping
"""

import subprocess
import os
from pathlib import Path
import yaml

def setup_cron_job():
    """Setup cron job for automatic scraping"""
    print("🔧 Setting up cron job for automatic job scraping...")
    
    # Get current directory
    current_dir = Path(__file__).resolve().parent
    scraper_script = current_dir / "scraper_only.py"
    
    # Check if scraper script exists
    if not scraper_script.exists():
        print(f"❌ Scraper script not found: {scraper_script}")
        return False
    
    # Load config to get cron schedule
    config_file = current_dir / "config_scraper.yaml"
    if config_file.exists():
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        cron_schedule = config.get('cron_schedule', '0 8 * * *')  # Default: daily at 8 AM
    else:
        cron_schedule = '0 8 * * *'  # Default: daily at 8 AM
    
    # Create cron command
    cron_command = f"{cron_schedule} cd {current_dir} && python3 {scraper_script} >> scraper.log 2>&1"
    
    print(f"📅 Cron schedule: {cron_schedule}")
    print(f"📁 Working directory: {current_dir}")
    print(f"🐍 Script: {scraper_script}")
    
    try:
        # Check if cron job already exists
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        existing_crontab = result.stdout if result.returncode == 0 else ""
        
        # Check if our job is already there
        if str(scraper_script) in existing_crontab:
            print("⚠️ Cron job already exists!")
            return True
        
        # Add new cron job
        new_crontab = existing_crontab + f"\n# Job scraping automation\n{cron_command}\n"
        
        # Write to temporary file
        temp_file = "/tmp/new_crontab"
        with open(temp_file, 'w') as f:
            f.write(new_crontab)
        
        # Install new crontab
        result = subprocess.run(['crontab', temp_file], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Cron job installed successfully!")
            print(f"📝 Job will run: {cron_schedule}")
            print(f"📄 Logs will be saved to: {current_dir}/scraper.log")
            
            # Clean up temp file
            os.remove(temp_file)
            return True
        else:
            print(f"❌ Failed to install cron job: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error setting up cron: {e}")
        return False

def remove_cron_job():
    """Remove the cron job"""
    print("🗑️ Removing cron job...")
    
    try:
        # Get current crontab
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        if result.returncode != 0:
            print("No existing crontab found.")
            return True
        
        current_dir = Path(__file__).resolve().parent
        scraper_script = current_dir / "scraper_only.py"
        
        # Filter out our job
        lines = result.stdout.split('\n')
        filtered_lines = [line for line in lines if str(scraper_script) not in line and line.strip()]
        
        # Write filtered crontab
        if filtered_lines:
            temp_file = "/tmp/filtered_crontab"
            with open(temp_file, 'w') as f:
                f.write('\n'.join(filtered_lines) + '\n')
            
            result = subprocess.run(['crontab', temp_file], capture_output=True, text=True)
            os.remove(temp_file)
            
            if result.returncode == 0:
                print("✅ Cron job removed successfully!")
                return True
            else:
                print(f"❌ Failed to remove cron job: {result.stderr}")
                return False
        else:
            # Remove all crontab
            result = subprocess.run(['crontab', '-r'], capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ All cron jobs removed!")
                return True
            else:
                print(f"❌ Failed to remove crontab: {result.stderr}")
                return False
                
    except Exception as e:
        print(f"❌ Error removing cron job: {e}")
        return False

def show_cron_status():
    """Show current cron jobs"""
    print("📋 Current cron jobs:")
    print("-" * 50)
    
    try:
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            print(result.stdout)
        else:
            print("No cron jobs found.")
    except Exception as e:
        print(f"❌ Error checking cron jobs: {e}")

def main():
    """Main function"""
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "install":
            setup_cron_job()
        elif command == "remove":
            remove_cron_job()
        elif command == "status":
            show_cron_status()
        else:
            print("Usage: python3 setup_cron.py [install|remove|status]")
    else:
        print("🔧 Cron Job Setup for Job Scraping")
        print("=" * 40)
        print("Commands:")
        print("  install  - Install cron job for automatic scraping")
        print("  remove   - Remove the cron job")
        print("  status   - Show current cron jobs")
        print()
        print("Example: python3 setup_cron.py install")

if __name__ == "__main__":
    main() 