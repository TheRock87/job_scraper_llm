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
import time
import importlib

import pandas as pd
import yaml
from jobspy.model import Country

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Add the directory containing both job_filter_app and jobspy to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
# Also add the current working directory (for GitHub Actions)
cwd = Path.cwd()
if str(cwd) not in sys.path:
    sys.path.insert(0, str(cwd))

try:
    from jobspy import scrape_jobs
    logging.info("[✅] jobspy imported successfully!")
except Exception as e:
    logging.error("[❌] jobspy import failed: %s", e)
    raise

logging.info(f"Current working directory: {os.getcwd()}")

def load_config():
    """Load and validate configuration"""
    logging.info("🔍 Loading configuration...")
    try:
        config_path = Path(__file__).resolve().parent / "config.yaml"
        logging.info(f"Looking for config at: {config_path} (exists: {config_path.exists()})")
        with open(config_path, "r") as f:
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
        for term in re.split(r"\s+OR\s+", config["search_term"]) 
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
    
    # Log proxy configuration
    proxies = config.get("proxies", [])
    if proxies:
        logging.info("  Proxies configured: %d", len(proxies))
        logging.info("  Proxy fallback: Enabled (will continue without proxies if all fail)")
    else:
        logging.info("  Proxies: None configured")
    
    # Store all jobs here
    all_jobs = []
    
    # Group locations by country for country-wide search
    from collections import defaultdict
    country_to_locations = defaultdict(list)
    mentioned_countries = set()
    for location in locations:
        matched_country = None
        for country in Country:
            country_names = [n.strip().lower() for n in country.value[0].split(",")]
            for name in country_names:
                if name and name in location.lower():
                    matched_country = country
                    break
            if matched_country:
                break
        if matched_country:
            country_to_locations[matched_country].append(location)
            mentioned_countries.add(matched_country)
    
    # Calculate total searches including country-wide searches
    # Each search term gets: len(locations) + len(mentioned_countries excluding Egypt)
    country_wide_searches = len([c for c in mentioned_countries if c.value[0].strip().lower() != "egypt"])
    total_searches = len(search_terms) * (len(locations) + country_wide_searches)
    current_search = 0
    
    for search_term in search_terms:
        countries_done = set()
        for location in locations:
            current_search += 1
            logging.info("\n[%d/%d] 🔍 Scraping '%s' in %s", current_search, total_searches, search_term, location)
            logging.info("    → Starting search for '%s' in '%s'...", search_term, location)

            # --- Robust country extraction using Country enum ---
            country_indeed = None
            location_clean = location
            matched_country = None
            for country in Country:
                country_names = [n.strip().lower() for n in country.value[0].split(",")]
                for name in country_names:
                    if name and name in location.lower():
                        matched_country = country
                        break
                if matched_country:
                    break
            if matched_country:
                country_indeed = matched_country.value[0]  # Use original string, not title-cased
                # Remove country name from location for Indeed/Glassdoor
                for name in matched_country.value[0].split(","):
                    location_clean = re.sub(r",?\\s*" + re.escape(name), "", location_clean, flags=re.IGNORECASE)
                location_clean = location_clean.strip(", ").strip()
            else:
                country_indeed = None
                location_clean = location

            # --- Determine supported sites for this country ---
            glassdoor_supported = [c for c in Country if len(c.value) == 3]
            is_glassdoor_supported = matched_country in glassdoor_supported if matched_country else False
            # Always include Indeed if country_indeed is set
            # Add Glassdoor only if supported
            extra_sites = ["indeed"]
            if is_glassdoor_supported:
                extra_sites.append("glassdoor")
            # Add ZipRecruiter only for Ireland
            if matched_country and matched_country.value[0].strip().lower() == "ireland":
                extra_sites.append("zip_recruiter")
            # Merge with config site_name
            if isinstance(site_name, list):
                sites_for_this_location = list(set(site_name + extra_sites))
            else:
                sites_for_this_location = list(set([site_name] + extra_sites))
            # Remove ZipRecruiter for non-Ireland
            if not (matched_country and matched_country.value[0].strip().lower() == "ireland"):
                sites_for_this_location = [s for s in sites_for_this_location if s.lower() != "zip_recruiter"]
            try:
                # Prepare scrape_jobs parameters
                scrape_params = {
                    'site_name': sites_for_this_location,
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
                # Add proxies from config
                if proxies:
                    scrape_params['proxies'] = proxies
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
        # After all locations, do a country-wide search for each country (except Egypt), but only for countries mentioned in config
        for matched_country in mentioned_countries:
            if matched_country.value[0].strip().lower() == "egypt":
                continue
            if matched_country in countries_done:
                continue
            countries_done.add(matched_country)
            current_search += 1
            country_indeed = matched_country.value[0]
            logging.info("\n[%d/%d] 🔍 Scraping '%s' in %s (country-wide)", current_search, total_searches, search_term, country_indeed)
            logging.info("    → Starting country-wide search for '%s' in '%s'...", search_term, country_indeed)
            # Only include country name, no city/state
            location_clean = None  # or ''
            # --- Determine supported sites for this country ---
            glassdoor_supported = [c for c in Country if len(c.value) == 3]
            is_glassdoor_supported = matched_country in glassdoor_supported
            extra_sites = ["indeed"]
            if is_glassdoor_supported:
                extra_sites.append("glassdoor")
            # Add ZipRecruiter only for Ireland
            if matched_country.value[0].strip().lower() == "ireland":
                extra_sites.append("zip_recruiter")
            # Merge with config site_name
            if isinstance(site_name, list):
                sites_for_this_location = list(set(site_name + extra_sites))
            else:
                sites_for_this_location = list(set([site_name] + extra_sites))
            # Remove ZipRecruiter for non-Ireland
            if matched_country.value[0].strip().lower() != "ireland":
                sites_for_this_location = [s for s in sites_for_this_location if s.lower() != "zip_recruiter"]
            try:
                scrape_params = {
                    'site_name': sites_for_this_location,
                    'search_term': f'"{search_term}"',
                    'location': location_clean,
                    'results_wanted': results_wanted,
                    'hours_old': hours_old,
                    'linkedin_fetch_description': linkedin_fetch_description,
                    'description_format': description_format,
                    'verbose': 1,
                }
                if country_indeed:
                    scrape_params['country_indeed'] = country_indeed
                # Add proxies from config
                if proxies:
                    scrape_params['proxies'] = proxies
                jobs = scrape_jobs(**scrape_params)
                if not jobs.empty:
                    jobs["search_term"] = search_term
                    jobs["search_location"] = country_indeed + " (country-wide)"
                    all_jobs.append(jobs)
                    logging.info("    ✅ Finished: %d jobs found for '%s' in '%s' (country-wide)", len(jobs), search_term, country_indeed)
                else:
                    logging.warning("    ⚠️ No jobs found for '%s' in '%s' (country-wide)", search_term, country_indeed)
            except Exception as e:
                logging.error("    ❌ Failed: %s for '%s' in '%s' (country-wide)", e, search_term, country_indeed)
                continue
        # After all locations for this search_term, wait 60 seconds
        logging.info("⏳ Waiting 60 seconds before next search term to avoid rate limits...")
        time.sleep(60)
    
    # Combine results
    if not all_jobs:
        logging.warning("\n🚫 No job listings were found.")
        return None

    # Filter out empty DataFrames before concatenation
    non_empty_jobs = [df for df in all_jobs if not df.empty]
    if not non_empty_jobs:
        logging.warning("\n🚫 All job DataFrames are empty after filtering. No jobs to process.")
        return None

    df = pd.concat(non_empty_jobs, ignore_index=True).drop_duplicates(
        subset=["title", "company", "location"]
    )
    
    logging.info("\n📊 Scraping Summary:")
    logging.info("  Total jobs found: %d", len(df))
    logging.info("  Unique jobs after deduplication: %d", len(df))
    logging.info("  Search terms processed: %d", len(search_terms))
    logging.info("  Locations processed: %d", len(locations))
    logging.info("  Country-wide searches: %d", country_wide_searches)
    logging.info("  Total searches performed: %d", total_searches)
    
    return df

def save_to_csv(df, output_path="jobs_raw.csv"):
    """Save jobs to CSV file"""
    logging.info("\n💾 Saving jobs to %s...", output_path)
    
    # Ensure the data directory exists if the path includes it
    output_file = Path(output_path)
    if output_file.parent.name == "data":
        output_file.parent.mkdir(exist_ok=True)
    
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
    output_file = config.get("output_file", "data/jobs_raw.csv")
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