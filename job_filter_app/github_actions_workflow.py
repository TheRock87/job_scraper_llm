#!/usr/bin/env python3
"""
GitHub Actions Workflow Script for Job Processing
Handles job deduplication and tracks new jobs between scrapes
"""

import pandas as pd
import json
import os
import hashlib
from datetime import datetime
from pathlib import Path
import sys

def create_job_hash(job_row):
    """Create a unique hash for a job based on key fields"""
    # Combine key identifying fields
    key_fields = [
        str(job_row.get('title', '')),
        str(job_row.get('company', '')),
        str(job_row.get('location', '')),
        str(job_row.get('job_url', ''))
    ]
    
    # Create hash from combined string
    combined = '|'.join(key_fields).lower().strip()
    return hashlib.md5(combined.encode()).hexdigest()

def load_previous_jobs(history_file):
    """Load previously processed jobs from history file"""
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r') as f:
                history = json.load(f)
            return history
        except Exception as e:
            print(f"⚠️ Error loading history: {e}")
            return {}
    return {}

def save_job_history(jobs_data, history_file):
    """Save job history to file"""
    try:
        with open(history_file, 'w') as f:
            json.dump(jobs_data, f, indent=2)
        print(f"✅ Job history saved to {history_file}")
    except Exception as e:
        print(f"❌ Error saving history: {e}")

def process_new_jobs(csv_file, history_file, output_dir):
    """Process jobs and identify new ones"""
    print("🔄 Processing jobs for GitHub Actions...")
    
    # Load current jobs
    if not os.path.exists(csv_file):
        print(f"❌ CSV file not found: {csv_file}")
        return None, None
    
    df = pd.read_csv(csv_file)
    print(f"📊 Loaded {len(df)} jobs from {csv_file}")
    
    # Load previous job history
    previous_jobs = load_previous_jobs(history_file)
    
    # Create hash for each current job
    df['job_hash'] = df.apply(create_job_hash, axis=1)
    
    # Identify new jobs
    new_jobs = []
    existing_jobs = []
    
    for _, job in df.iterrows():
        job_hash = job['job_hash']
        if job_hash not in previous_jobs:
            new_jobs.append(job)
        else:
            existing_jobs.append(job)
    
    print(f"📈 New jobs found: {len(new_jobs)}")
    print(f"📋 Existing jobs: {len(existing_jobs)}")
    
    # Update job history with all current jobs
    current_jobs_data = {}
    for _, job in df.iterrows():
        job_hash = job['job_hash']
        current_jobs_data[job_hash] = {
            'title': job.get('title', ''),
            'company': job.get('company', ''),
            'location': job.get('location', ''),
            'job_url': job.get('job_url', ''),
            'first_seen': previous_jobs.get(job_hash, {}).get('first_seen', datetime.now().isoformat()),
            'last_seen': datetime.now().isoformat()
        }
    
    # Save updated history
    save_job_history(current_jobs_data, history_file)
    
    # Create output files
    if new_jobs:
        new_df = pd.DataFrame(new_jobs)
        new_jobs_file = os.path.join(output_dir, 'new_jobs.csv')
        new_df.to_csv(new_jobs_file, index=False)
        print(f"✅ New jobs saved to: {new_jobs_file}")
    else:
        new_jobs_file = None
    
    # Save all jobs for processing
    all_jobs_file = os.path.join(output_dir, 'all_jobs.csv')
    df.to_csv(all_jobs_file, index=False)
    print(f"✅ All jobs saved to: {all_jobs_file}")
    
    return new_jobs_file, all_jobs_file

def create_summary_report(new_jobs_file, all_jobs_file, output_dir):
    """Create a summary report for GitHub Actions"""
    summary = {
        'timestamp': datetime.now().isoformat(),
        'new_jobs_count': 0,
        'total_jobs_count': 0,
        'has_new_jobs': False
    }
    
    if all_jobs_file and os.path.exists(all_jobs_file):
        df = pd.read_csv(all_jobs_file)
        summary['total_jobs_count'] = len(df)
    
    if new_jobs_file and os.path.exists(new_jobs_file):
        new_df = pd.read_csv(new_jobs_file)
        summary['new_jobs_count'] = len(new_df)
        summary['has_new_jobs'] = len(new_df) > 0
    
    # Save summary
    summary_file = os.path.join(output_dir, 'summary.json')
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"📊 Summary saved to: {summary_file}")
    return summary

def main():
    """Main function for GitHub Actions"""
    # Get paths from environment or use defaults
    csv_file = os.environ.get('CSV_FILE', 'jobs_raw.csv')
    history_file = os.environ.get('HISTORY_FILE', 'job_history.json')
    output_dir = os.environ.get('OUTPUT_DIR', 'processed_jobs')
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    print("🚀 GitHub Actions Job Processing")
    print("=" * 50)
    print(f"📄 Input CSV: {csv_file}")
    print(f"📚 History file: {history_file}")
    print(f"📁 Output directory: {output_dir}")
    
    # Process jobs
    new_jobs_file, all_jobs_file = process_new_jobs(csv_file, history_file, output_dir)
    
    if new_jobs_file is None:
        print("❌ Processing failed")
        sys.exit(1)
    
    # Create summary
    summary = create_summary_report(new_jobs_file, all_jobs_file, output_dir)
    
    # Print results for GitHub Actions
    print("\n📊 Processing Results:")
    print(f"  Total jobs: {summary['total_jobs_count']}")
    print(f"  New jobs: {summary['new_jobs_count']}")
    print(f"  Has new jobs: {summary['has_new_jobs']}")
    
    # Set GitHub Actions output
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write(f"new_jobs_count={summary['new_jobs_count']}\n")
            f.write(f"total_jobs_count={summary['total_jobs_count']}\n")
            f.write(f"has_new_jobs={str(summary['has_new_jobs']).lower()}\n")
            f.write(f"new_jobs_file={new_jobs_file or ''}\n")
            f.write(f"all_jobs_file={all_jobs_file or ''}\n")
    
    print("\n✅ GitHub Actions processing complete!")

if __name__ == "__main__":
    main() 