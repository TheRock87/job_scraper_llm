#!/usr/bin/env python3
"""
Simplified Job Scraping Script
This script scrapes jobs and saves them to jobs_raw.csv, then uploads to Google Drive
"""

import logging
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

current_dir = Path(__file__).resolve().parent
jobspy_path = current_dir.parent
logging.info("[🧪] Adding to sys.path: %s", jobspy_path)
sys.path.insert(0, str(jobspy_path))

try:
    from jobspy import scrape_jobs
    logging.info("[✅] jobspy imported successfully!")
except Exception as e:
    logging.error("[❌] jobspy import failed: %s", e)
    raise

def load_config():
    """Load and validate configuration"""
    logging.info("🔍 Loading configuration...")
    try:
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
        
        # Validate required fields
        required_fields = ["search_term", "locations", "site_name", "results_wanted"]
        for field in required_fields:
            if field not in config:
                logging.error("❌ Missing required field: %s", field)
                return None
        
        logging.info("✅ Configuration loaded successfully!")
        return config
    except FileNotFoundError:
        logging.error("❌ config.yaml not found")
        return None
    except yaml.YAMLError as e:
        logging.error("❌ Error parsing config.yaml: %s", e)
        return None

def scrape_jobs_with_progress(config):
    """Scrape jobs with enhanced progress tracking"""
    logging.info("\n🚀 Starting job scraping...")
    logging.info("=" * 50)
    
    # Parse search terms
    search_terms = [
        term.strip().strip('"') 
        for term in re.split(r"\\s+OR\\s+", config["search_term"]) 
        if not term.startswith("-")  # Exclude negative terms
    ]
    
    locations = config["locations"]
    site_name = config["site_name"]
    results_wanted = config["results_wanted"]
    hours_old = config["hours_old"]
    linkedin_fetch_description = config.get("linkedin_fetch_description", False)
    description_format = config.get("description_format", "markdown")
    
    logging.info("📋 Configuration:")
    logging.info("  Search terms: %s", search_terms)
    logging.info("  Locations: %s", locations)
    logging.info("  Sites: %s", site_name)
    logging.info("  Results per search: %s", results_wanted)
    logging.info("  Hours old: %s", hours_old)
    
    # Store all jobs here
    all_jobs = []
    total_searches = len(search_terms) * len(locations)
    current_search = 0
    
    for search_term in search_terms:
        for location in locations:
            current_search += 1
            logging.info("\n[%d/%d] 🔍 Scraping '%s' in %s", current_search, total_searches, search_term, location)
            logging.info("    → Starting search for '%s' in '%s'...", search_term, location)
            # Fix: Properly format country strings
            if "UAE" in location.upper() or "United Arab Emirates" in location:
                country_indeed = "United Arab Emirates"
                location_clean = location.replace("UAE", "").replace("United Arab Emirates", "").strip(", ").strip()
            elif "EGYPT" in location.upper():
                country_indeed = "Egypt"
                location_clean = location.replace("EGYPT", "").strip(", ").strip()
            elif "SAUDI ARABIA" in location.upper():
                country_indeed = "Saudi Arabia"
                location_clean = location.replace("Saudi Arabia", "").strip(", ").strip()
            elif "KUWAIT" in location.upper():
                country_indeed = "Kuwait"
                location_clean = location.replace("Kuwait", "").strip(", ").strip()
            elif "QATAR" in location.upper():
                country_indeed = "Qatar"
                location_clean = location.replace("Qatar", "").strip(", ").strip()
            elif "OMAN" in location.upper():
                country_indeed = "Oman"
                location_clean = location.replace("Oman", "").strip(", ").strip()
            elif "BAHRAIN" in location.upper():
                country_indeed = "Bahrain"
                location_clean = location.replace("Bahrain", "").strip(", ").strip()
            elif "GERMANY" in location.upper():
                country_indeed = "Germany"
                location_clean = location.replace("Germany", "").strip(", ").strip()
            elif "SPAIN" in location.upper():
                country_indeed = "Spain"
                location_clean = location.replace("Spain", "").strip(", ").strip()
            elif "UK" in location.upper() or "UNITED KINGDOM" in location.upper():
                country_indeed = "UK"
                location_clean = location.replace("UK", "").replace("United Kingdom", "").strip(", ").strip()
            elif "AUSTRIA" in location.upper():
                country_indeed = "Austria"
                location_clean = location.replace("Austria", "").strip(", ").strip()
            elif "CANADA" in location.upper():
                country_indeed = "Canada"
                location_clean = location.replace("Canada", "").strip(", ").strip()
            elif "IRELAND" in location.upper():
                country_indeed = "Ireland"
                location_clean = location.replace("Ireland", "").strip(", ").strip()
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
                    logging.info("    ✅ Finished: %d jobs found for '%s' in '%s'", len(jobs), search_term, location)
                else:
                    logging.warning("    ⚠️ No jobs found for '%s' in '%s'", search_term, location)
            except Exception as e:
                logging.error("    ❌ Failed: %s for '%s' in '%s'", e, search_term, location)
                continue
    
    # Combine results
    if not all_jobs:
        logging.warning("\n🚫 No job listings were found.")
        return None

    df = pd.concat(all_jobs, ignore_index=True).drop_duplicates(
        subset=["title", "company", "location"]
    )
    
    logging.info("\n📊 Scraping Summary:")
    logging.info("  Total jobs found: %d", len(df))
    logging.info("  Unique jobs after deduplication: %d", len(df))
    logging.info("  Search terms processed: %d", len(search_terms))
    logging.info("  Locations processed: %d", len(locations))
    
    return df

def save_to_csv(df, output_path="jobs_raw.csv"):
    """Save jobs to CSV file"""
    logging.info("\n💾 Saving jobs to %s...", output_path)
    
    try:
        df.to_csv(output_path, index=False)
        logging.info("✅ Successfully saved %d jobs to %s", len(df), output_path)
        return True
    except Exception as e:
        logging.error("❌ Failed to save CSV: %s", e)
        return False

def upload_to_gdrive(local_file, remote_folder="gdrive:AI-Jobs"):
    """Upload file to Google Drive using rclone"""
    logging.info("\n☁️ Uploading %s to Google Drive...", local_file)
    
    try:
        # Check if rclone is installed
        result = subprocess.run(["rclone", "version"], capture_output=True, text=True)
        if result.returncode != 0:
            logging.warning("❌ rclone is not installed locally. Skipping Google Drive upload.")
            logging.warning("   This is normal when running locally - upload will happen in GitHub Actions.")
            return False
        
        # Upload file
        cmd = ["rclone", "copy", local_file, remote_folder, "--progress"]
        logging.info("Running: %s", ' '.join(cmd))
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logging.info("✅ Successfully uploaded %s to %s", local_file, remote_folder)
            return True
        else:
            logging.error("❌ Upload failed: %s", result.stderr)
            return False
            
    except FileNotFoundError:
        logging.warning("❌ rclone is not installed locally. Skipping Google Drive upload.")
        logging.warning("   This is normal when running locally - upload will happen in GitHub Actions.")
        return False
    except Exception as e:
        logging.error("❌ Upload error: %s", e)
        return False

def main():
    """Main scraping workflow"""
    logging.info("🔍 Job Scraping Workflow (Local)")
    logging.info("=" * 50)
    
    # Step 1: Load configuration
    config = load_config()
    if not config:
        sys.exit(1)
    
    # Step 2: Scrape jobs
    jobs_df = scrape_jobs_with_progress(config)
    
    if jobs_df is None or jobs_df.empty:
        logging.warning("⏹️ No jobs were scraped, exiting.")
        sys.exit(0)
    
    # Step 3: Save to CSV
    output_file = config.get("output_file", "jobs_raw.csv")
    if not save_to_csv(jobs_df, output_file):
        sys.exit(1)
    
    # Step 4: Upload to Google Drive (optional)
    if config.get("upload_to_gdrive", False):
        gdrive_folder = config.get("gdrive_folder", "gdrive:AI-Jobs")
        upload_to_gdrive(output_file, gdrive_folder)

    logging.info("\n" + "=" * 50)
    logging.info("🎉 SCRAPING COMPLETED!")
    logging.info("=" * 50)
    logging.info("📊 Total jobs scraped: %d", len(jobs_df))
    logging.info("📄 Local file: %s", output_file)
    if not config.get("upload_to_gdrive", False):
        logging.info("☁️ Upload skipped as per config.")
    elif config.get("upload_to_gdrive", False) and 'rclone' not in os.popen('command -v rclone').read():
         logging.info("☁️ Upload skipped (rclone not available locally)")
    
    logging.info("📝 Next step: Run the Google Colab notebook to process with LLM")

if __name__ == "__main__":
    main() 