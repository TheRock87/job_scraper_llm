#!/usr/bin/env python3
"""
Simplified Job Scraping Script
This script scrapes jobs and saves them to jobs_raw.csv, then uploads to Google Drive
"""

import yaml
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path
import re
import subprocess
import os

current_dir = Path(__file__).resolve().parent
jobspy_path = current_dir.parent
print("[🧪] Adding to sys.path:", jobspy_path)
sys.path.insert(0, str(jobspy_path))

try:
    from jobspy import scrape_jobs
    print("[✅] jobspy imported successfully!")
except Exception as e:
    print("[❌] jobspy import failed:", e)
    raise

def load_config():
    """Load and validate configuration"""
    print("🔍 Loading configuration...")
    try:
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
        
        # Validate required fields
        required_fields = ["search_term", "locations", "site_name", "results_wanted"]
        for field in required_fields:
            if field not in config:
                print(f"❌ Missing required field: {field}")
                return None
        
        print("✅ Configuration loaded successfully!")
        return config
    except FileNotFoundError:
        print("❌ config.yaml not found")
        return None
    except yaml.YAMLError as e:
        print(f"❌ Error parsing config.yaml: {e}")
        return None

def scrape_jobs_with_progress(config):
    """Scrape jobs with enhanced progress tracking"""
    print("\n🚀 Starting job scraping...")
    print("=" * 50)
    
    # Parse search terms
    search_terms = [
        term.strip().strip('"') 
        for term in re.split(r"\s+OR\s+", config["search_term"]) 
        if not term.startswith("-")  # Exclude negative terms
    ]
    
    locations = config["locations"]
    site_name = config["site_name"]
    results_wanted = config["results_wanted"]
    hours_old = config["hours_old"]
    linkedin_fetch_description = config.get("linkedin_fetch_description", False)
    description_format = config.get("description_format", "markdown")
    
    print(f"📋 Configuration:")
    print(f"  Search terms: {search_terms}")
    print(f"  Locations: {locations}")
    print(f"  Sites: {site_name}")
    print(f"  Results per search: {results_wanted}")
    print(f"  Hours old: {hours_old}")
    
    # Store all jobs here
    all_jobs = []
    total_searches = len(search_terms) * len(locations)
    current_search = 0
    
    for search_term in search_terms:
        for location in locations:
            current_search += 1
            print(f"\n[{current_search}/{total_searches}] 🔍 Scraping '{search_term}' in {location}")
            
            # Fix: Properly format country strings
            if "UAE" in location.upper() or "United Arab Emirates" in location:
                country_indeed = "united arab emirates"
                location_clean = location.replace("UAE", "").replace("United Arab Emirates", "").strip(", ").strip()
            elif "EGYPT" in location.upper():
                country_indeed = "egypt"
                location_clean = location.replace("EGYPT", "").strip(", ").strip()
            else:
                country_indeed = None
                location_clean = location

            try:
                # Prepare scrape_jobs parameters
                scrape_params = {
                    'site_name': site_name,
                    'search_term': f'"{search_term}"',
                    'location': location_clean,
                    'results_wanted': results_wanted,
                    'hours_old': hours_old,
                    'linkedin_fetch_description': linkedin_fetch_description,
                    'description_format': description_format,
                    'verbose': 1,
                }
                
                # Add country_indeed only if it's not None
                if country_indeed:
                    scrape_params['country_indeed'] = country_indeed
                
                jobs = scrape_jobs(**scrape_params)
                
                if not jobs.empty:
                    jobs["search_term"] = search_term
                    jobs["search_location"] = location
                    all_jobs.append(jobs)
                    print(f"  ✅ Found {len(jobs)} jobs")
                else:
                    print(f"  ⚠️ No jobs found")
                    
            except Exception as e:
                print(f"  ❌ Failed: {e}")
                continue
    
    # Combine results
    if not all_jobs:
        print("\n🚫 No job listings were found.")
        return None

    df = pd.concat(all_jobs, ignore_index=True).drop_duplicates(
        subset=["title", "company", "location"]
    )
    
    print(f"\n📊 Scraping Summary:")
    print(f"  Total jobs found: {len(df)}")
    print(f"  Unique jobs after deduplication: {len(df)}")
    print(f"  Search terms processed: {len(search_terms)}")
    print(f"  Locations processed: {len(locations)}")
    
    return df

def save_to_csv(df, output_path="jobs_raw.csv"):
    """Save jobs to CSV file"""
    print(f"\n💾 Saving jobs to {output_path}...")
    
    try:
        df.to_csv(output_path, index=False)
        print(f"✅ Successfully saved {len(df)} jobs to {output_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to save CSV: {e}")
        return False

def upload_to_gdrive(local_file, remote_folder="gdrive:AI-Jobs"):
    """Upload file to Google Drive using rclone"""
    print(f"\n☁️ Uploading {local_file} to Google Drive...")
    
    try:
        # Check if rclone is installed
        result = subprocess.run(["rclone", "version"], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ rclone is not installed. Please install rclone first.")
            print("   Visit: https://rclone.org/install/")
            return False
        
        # Upload file
        cmd = ["rclone", "copy", local_file, remote_folder, "--progress"]
        print(f"Running: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Successfully uploaded {local_file} to {remote_folder}")
            return True
        else:
            print(f"❌ Upload failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return False

def main():
    """Main scraping workflow"""
    print("🔍 Job Scraping Workflow (Local)")
    print("=" * 50)
    
    # Step 1: Load configuration
    config = load_config()
    if not config:
        sys.exit(1)
    
    # Step 2: Scrape jobs
    df = scrape_jobs_with_progress(config)
    if df is None:
        print("❌ No jobs found. Exiting.")
        sys.exit(1)
    
    # Step 3: Save to CSV
    output_file = "jobs_raw.csv"
    if not save_to_csv(df, output_file):
        sys.exit(1)
    
    # Step 4: Upload to Google Drive
    if not upload_to_gdrive(output_file):
        print("⚠️ Upload to Google Drive failed, but local file was saved.")
    
    # Final summary
    print("\n" + "=" * 50)
    print("🎉 SCRAPING COMPLETED!")
    print("=" * 50)
    print(f"📊 Total jobs scraped: {len(df)}")
    print(f"📄 Local file: {output_file}")
    print(f"☁️ Uploaded to: gdrive:AI-Jobs/{output_file}")
    print("\n📝 Next step: Run the Google Colab notebook to process with LLM")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️ Scraping stopped by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Scraping failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 