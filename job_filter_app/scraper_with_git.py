#!/usr/bin/env python3
"""
Enhanced Job Scraper with Git Integration and Google Drive Upload
Automatically commits scraped jobs to trigger GitHub Actions and uploads to Google Drive for Colab
"""

import yaml
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path
import re
import subprocess
import os
import json

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
        with open("config_scraper.yaml", "r") as f:
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
        print("❌ config_scraper.yaml not found")
        return None
    except yaml.YAMLError as e:
        print(f"❌ Error parsing config_scraper.yaml: {e}")
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

def check_git_status():
    """Check if we're in a git repository"""
    try:
        result = subprocess.run(["git", "status"], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def commit_to_git(csv_file, job_count):
    """Commit the CSV file to git to trigger GitHub Actions"""
    print(f"\n🔄 Committing to Git to trigger GitHub Actions...")
    
    try:
        # Check if git is available
        if not check_git_status():
            print("⚠️ Not in a git repository or git not available")
            return False
        
        # Add the CSV file
        result = subprocess.run(["git", "add", csv_file], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Failed to add file to git: {result.stderr}")
            return False
        
        # Commit with descriptive message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_message = f"📊 Update jobs - {job_count} jobs scraped at {timestamp}"
        
        result = subprocess.run(["git", "commit", "-m", commit_message], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Failed to commit: {result.stderr}")
            return False
        
        print(f"✅ Committed: {commit_message}")
        
        # Push to remote
        result = subprocess.run(["git", "push"], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Failed to push: {result.stderr}")
            return False
        
        print("✅ Pushed to remote repository")
        print("🚀 GitHub Actions workflow will be triggered automatically!")
        
        return True
        
    except Exception as e:
        print(f"❌ Git operation failed: {e}")
        return False

def create_scraping_summary(df, config):
    """Create a summary of the scraping session"""
    summary = {
        'timestamp': datetime.now().isoformat(),
        'total_jobs': len(df),
        'search_terms': re.split(r"\s+OR\s+", config["search_term"]),
        'locations': config["locations"],
        'sites': config["site_name"],
        'results_per_search': config["results_wanted"],
        'hours_old': config["hours_old"]
    }
    
    # Save summary
    summary_file = "scraping_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"📊 Scraping summary saved to: {summary_file}")
    return summary

def main():
    """Main scraping workflow with Git integration and Google Drive upload"""
    print("🔍 Job Scraping Workflow with Git + Google Drive Integration")
    print("=" * 70)
    
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
    gdrive_success = upload_to_gdrive(output_file)
    
    # Step 5: Create summary
    summary = create_scraping_summary(df, config)
    
    # Step 6: Commit to Git (if available)
    git_success = commit_to_git(output_file, len(df))
    
    # Final summary
    print("\n" + "=" * 70)
    print("🎉 SCRAPING COMPLETED!")
    print("=" * 70)
    print(f"📊 Total jobs scraped: {len(df)}")
    print(f"📄 Local file: {output_file}")
    
    if gdrive_success:
        print("✅ Google Drive upload successful")
        print("📱 File available for Colab processing")
    else:
        print("⚠️ Google Drive upload failed")
        print("📝 You can manually upload the CSV file")
    
    if git_success:
        print("✅ Git commit successful")
        print("🚀 GitHub Actions workflow triggered!")
        print("📋 Check your GitHub repository for processing results")
    else:
        print("⚠️ Git operations failed")
        print("📝 You can manually commit and push to trigger GitHub Actions")
    
    print(f"\n📊 Scraping Summary:")
    print(f"  Search terms: {summary['search_terms']}")
    print(f"  Locations: {summary['locations']}")
    print(f"  Job sites: {summary['sites']}")
    print(f"  Results per search: {summary['results_per_search']}")
    
    print(f"\n📝 Next Steps:")
    if gdrive_success:
        print("1. Open your Colab notebook")
        print("2. Mount Google Drive")
        print("3. Load jobs_raw.csv from AI-Jobs folder")
        print("4. Process with Mistral-7B model")
    if git_success:
        print("5. Check GitHub Actions for automated processing results")

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