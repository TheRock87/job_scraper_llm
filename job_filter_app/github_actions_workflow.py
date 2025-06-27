#!/usr/bin/env python3
"""
GitHub Actions Workflow Script for Job Processing
Handles job deduplication and tracks new jobs between scrapes
Saves all outputs directly to the data/ directory in JSON and CSV formats.
"""

import pandas as pd
import json
import os
import hashlib
from datetime import datetime
from pathlib import Path
import sys
import logging
import logging.config
import yaml
from pathlib import Path

# Load YAML logging config
config_path = Path(__file__).parent.parent / "config.yaml"
with open(config_path) as cf:
    full_cfg = yaml.safe_load(cf)
logging.config.dictConfig(full_cfg["logging"])
logger = logging.getLogger(__name__)

# Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
CSV_FILE = os.environ.get('CSV_FILE', str(DATA_DIR / 'jobs_raw.csv'))
HISTORY_FILE = os.environ.get('HISTORY_FILE', str(DATA_DIR / 'job_history.json'))
ALL_JOBS_FILE = DATA_DIR / 'all_jobs.csv'
NEW_JOBS_FILE = DATA_DIR / 'new_jobs.csv'
SUMMARY_FILE = DATA_DIR / 'summary.json'

def create_job_hash(job_row):
    """Create a unique hash for a job based on key fields"""
    key_fields = [
        str(job_row.get('title', '')),
        str(job_row.get('company', '')),
        str(job_row.get('location', '')),
        str(job_row.get('job_url', ''))
    ]
    combined = '|'.join(key_fields).lower().strip()
    return hashlib.md5(combined.encode()).hexdigest()

def load_previous_jobs(history_file):
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r') as f:
                history = json.load(f)
            return history
        except Exception as e:
            logging.warning(f"Error loading history: {e}")
            return {}
    return {}

def save_job_history(jobs_data, history_file):
    try:
        with open(history_file, 'w') as f:
            json.dump(jobs_data, f, indent=2)
        logging.info(f"Job history saved to {history_file}")
    except Exception as e:
        logging.error(f"Error saving history: {e}")

def process_new_jobs(csv_file, history_file):
    logging.info("Processing jobs for GitHub Actions...")
    if not os.path.exists(csv_file):
        logging.error(f"CSV file not found: {csv_file}")
        return None, None
    try:
        df = pd.read_csv(csv_file)
    except Exception as e:
        logging.error(f"Failed to read CSV: {e}")
        return None, None
    logging.info(f"Loaded {len(df)} jobs from {csv_file}")
    previous_jobs = load_previous_jobs(history_file)
    df['job_hash'] = df.apply(create_job_hash, axis=1)
    new_jobs = []
    for _, job in df.iterrows():
        job_hash = job['job_hash']
        if job_hash not in previous_jobs:
            new_jobs.append(job)
    logging.info(f"New jobs found: {len(new_jobs)}")
    logging.info(f"Existing jobs: {len(df) - len(new_jobs)}")
    # Update job history
    current_jobs_data = {}
    now = datetime.now().isoformat()
    for _, job in df.iterrows():
        job_hash = job['job_hash']
        current_jobs_data[job_hash] = {
            'title': job.get('title', ''),
            'company': job.get('company', ''),
            'location': job.get('location', ''),
            'job_url': job.get('job_url', ''),
            'first_seen': previous_jobs.get(job_hash, {}).get('first_seen', now),
            'last_seen': now
        }
    save_job_history(current_jobs_data, history_file)
    # Save new jobs
    if new_jobs:
        new_df = pd.DataFrame(new_jobs)
        try:
            new_df.to_csv(NEW_JOBS_FILE, index=False)
            logging.info(f"New jobs saved to: {NEW_JOBS_FILE}")
        except Exception as e:
            logging.error(f"Failed to save new_jobs.csv: {e}")
    else:
        try:
            if os.path.exists(NEW_JOBS_FILE):
                os.remove(NEW_JOBS_FILE)
                logging.info(f"No new jobs. Removed old {NEW_JOBS_FILE} if existed.")
        except Exception as e:
            logging.error(f"Failed to remove old new_jobs.csv: {e}")
    # Save all jobs
    try:
        df.to_csv(ALL_JOBS_FILE, index=False)
        logging.info(f"All jobs saved to: {ALL_JOBS_FILE}")
    except Exception as e:
        logging.error(f"Failed to save all_jobs.csv: {e}")
    return (str(NEW_JOBS_FILE) if new_jobs else None), str(ALL_JOBS_FILE)

def create_summary_report(new_jobs_file, all_jobs_file):
    summary = {
        'timestamp': datetime.now().isoformat(),
        'new_jobs_count': 0,
        'total_jobs_count': 0,
        'has_new_jobs': False
    }
    try:
        if all_jobs_file and os.path.exists(all_jobs_file):
            df = pd.read_csv(all_jobs_file)
            summary['total_jobs_count'] = len(df)
            summary['unique_companies'] = df['company'].nunique() if 'company' in df else 0
            summary['jobs_per_location'] = df['location'].value_counts().to_dict() if 'location' in df else {}
        if new_jobs_file and os.path.exists(new_jobs_file):
            new_df = pd.read_csv(new_jobs_file)
            summary['new_jobs_count'] = len(new_df)
            summary['has_new_jobs'] = len(new_df) > 0
    except Exception as e:
        logging.error(f"Failed to create summary: {e}")
    try:
        with open(SUMMARY_FILE, 'w') as f:
            json.dump(summary, f, indent=2)
        logging.info(f"Summary saved to: {SUMMARY_FILE}")
    except Exception as e:
        logging.error(f"Failed to save summary.json: {e}")
    return summary

def main():
    logging.info("GitHub Actions Job Processing")
    logging.info("=" * 50)
    logging.info(f"Input CSV: {CSV_FILE}")
    logging.info(f"History file: {HISTORY_FILE}")
    logging.info(f"Data directory: {DATA_DIR}")
    new_jobs_file, all_jobs_file = process_new_jobs(CSV_FILE, HISTORY_FILE)
    if all_jobs_file is None:
        logging.error("Processing failed because input CSV was not found.")
        sys.exit(1)
    summary = create_summary_report(new_jobs_file, all_jobs_file)
    logging.info("\nProcessing Results:")
    logging.info(f"  Total jobs: {summary.get('total_jobs_count', 0)}")
    logging.info(f"  New jobs: {summary.get('new_jobs_count', 0)}")
    logging.info(f"  Has new jobs: {summary.get('has_new_jobs', False)}")
    # Set GitHub Actions output
    github_output = os.environ.get('GITHUB_OUTPUT')
    if github_output:
        try:
            with open(github_output, 'a') as f:
                f.write(f"new_jobs_count={summary.get('new_jobs_count', 0)}\n")
                f.write(f"total_jobs_count={summary.get('total_jobs_count', 0)}\n")
                f.write(f"has_new_jobs={str(summary.get('has_new_jobs', False)).lower()}\n")
                f.write(f"new_jobs_file={new_jobs_file or ''}\n")
                f.write(f"all_jobs_file={all_jobs_file or ''}\n")
        except Exception as e:
            logging.error(f"Failed to write GitHub Actions output: {e}")
    logging.info("\n✅ GitHub Actions processing complete!")

if __name__ == "__main__":
    main() 
