# 🚀 GitHub Actions Automated Job Processing

This setup provides a complete automated workflow that scrapes jobs locally, commits them to GitHub, and automatically processes them with AI using GitHub Actions.

## 📋 Workflow Overview

### 🔄 Complete Automation Flow

1. **Local Scraping** → `scraper_with_git.py`
   - Scrapes jobs from multiple sources
   - Saves to `jobs_raw.csv`
   - Automatically commits to GitHub
   - Triggers GitHub Actions workflow

2. **GitHub Actions Processing** → `.github/workflows/job_processing.yml`
   - Identifies new jobs (deduplication)
   - Processes only new jobs with Mistral-7B
   - Creates interactive HTML output
   - Uploads results as artifacts
   - Updates job history

3. **Results** → GitHub Artifacts
   - `processed_jobs.csv` - All jobs with AI classifications
   - `filtered_jobs.html` - Interactive job table
   - `processing_summary.json` - Statistics and metadata

---

## 🛠️ Setup Instructions

### Step 1: Repository Setup

1. **Initialize Git repository** (if not already done):
   ```bash
   git init
   git remote add origin <your-github-repo-url>
   git branch -M main
   ```

2. **Create GitHub repository** and push your code:
   ```bash
   git add .
   git commit -m "Initial commit"
   git push -u origin main
   ```

### Step 2: GitHub Actions Setup

1. **Enable GitHub Actions** in your repository settings
2. **The workflow file** `.github/workflows/job_processing.yml` is already configured
3. **No additional setup needed** - it will run automatically

### Step 3: Local Environment Setup

1. **Install dependencies**:
   ```bash
   cd job_filter_app
   source .venv/bin/activate
   pip install pandas pyyaml requests
   ```

2. **Configure scraping** (edit `config_scraper.yaml`):
   ```yaml
   search_term: '"Ai engineer" OR "Machine learning engineer" OR "Data scientist"'
   results_wanted: 30
   locations:
     - Cairo, Egypt
     - Dubai, UAE
   ```

3. **Test the setup**:
   ```bash
   python test_setup.py
   ```

---

## 🚀 Usage

### Automated Workflow

1. **Run the enhanced scraper**:
   ```bash
   python scraper_with_git.py
   ```
   
   This will:
   - Scrape jobs from configured sources
   - Save to `jobs_raw.csv`
   - Commit and push to GitHub
   - Automatically trigger GitHub Actions

2. **Monitor GitHub Actions**:
   - Go to your repository → Actions tab
   - Watch the workflow run automatically
   - Download results from artifacts

### Manual Triggers

1. **Manual workflow trigger**:
   - Go to Actions → "🤖 AI Job Processing Workflow"
   - Click "Run workflow"
   - Choose to force process all jobs or only new ones

2. **Schedule-based triggers**:
   - Workflow runs daily at 9 AM UTC automatically
   - Can be modified in the workflow file

---

## 📊 Job Tracking System

### How New Job Detection Works

The system uses a sophisticated tracking mechanism:

1. **Job Hashing**: Each job gets a unique hash based on:
   - Job title
   - Company name
   - Location
   - Job URL

2. **History Tracking**: 
   - `job_history.json` stores all previously seen jobs
   - Tracks first seen and last seen dates
   - Persists between runs

3. **Deduplication**:
   - Only processes jobs not seen before
   - Saves processing time and costs
   - Maintains job history

### Files Generated

- `job_history.json` - Persistent job tracking database
- `processed_jobs/new_jobs.csv` - Only newly discovered jobs
- `processed_jobs/all_jobs.csv` - All jobs for processing
- `processed_jobs/summary.json` - Processing statistics

---

## 🔧 Configuration Options

### Workflow Triggers

The GitHub Actions workflow triggers on:

1. **Push to main branch** (when `jobs_raw.csv` changes)
2. **Daily schedule** (9 AM UTC)
3. **Manual trigger** (with force option)

### Customization

1. **Change schedule** in `.github/workflows/job_processing.yml`:
   ```yaml
   schedule:
     - cron: '0 9 * * *'  # Daily at 9 AM UTC
   ```

2. **Modify AI model** in the workflow:
   ```yaml
   model_name = "mistralai/Mistral-7B-Instruct-v0.2"
   ```

3. **Adjust processing parameters**:
   - Temperature, max tokens, etc.

---

## 📈 Monitoring and Results

### GitHub Actions Dashboard

1. **Workflow Status**: Check Actions tab for run status
2. **Logs**: Detailed logs for debugging
3. **Artifacts**: Download processed results
4. **Summary**: Automatic summary in workflow comments

### Results Files

1. **`filtered_jobs.html`**:
   - Interactive table with sortable columns
   - Clickable job URLs
   - Responsive design
   - Statistics dashboard

2. **`processed_jobs.csv`**:
   - All jobs with AI classifications
   - `Is_Junior_AI_Job` column (Yes/No/Uncertain)
   - Original data preserved

3. **`processing_summary.json`**:
   - Processing statistics
   - Timestamps
   - Relevance rates

---

## 🔍 Troubleshooting

### Common Issues

1. **GitHub Actions not triggering**:
   - Check repository permissions
   - Verify workflow file is in `.github/workflows/`
   - Ensure `jobs_raw.csv` is in the correct path

2. **No new jobs detected**:
   - Check `job_history.json` for existing jobs
   - Verify job hashing is working correctly
   - Use force processing option if needed

3. **Processing failures**:
   - Check GitHub Actions logs
   - Verify model loading (memory issues)
   - Check input file format

### Debugging

1. **Local testing**:
   ```bash
   python github_actions_workflow.py
   ```

2. **Check job history**:
   ```bash
   cat job_history.json | jq '. | length'
   ```

3. **Force reprocess**:
   - Use manual trigger with "force_process" option

---

## 💡 Advanced Features

### Conditional Processing

The workflow intelligently skips processing when:
- No new jobs are found
- Same jobs are scraped again
- Processing would be redundant

### Resource Optimization

- Uses 8-bit quantization for memory efficiency
- Processes only new jobs to save compute time
- Automatic artifact cleanup (30-day retention)

### Integration Options

1. **Slack/Discord notifications** (can be added)
2. **Email alerts** for new relevant jobs
3. **Webhook integration** for external systems

---

## 📝 Example Workflow Run

```
🚀 Starting automated job processing...
📊 Processing 45 jobs...
🔄 Loading Mistral-7B model...
✅ Model loaded!
📈 Processing jobs: 100%|██████████| 45/45 [02:30<00:00]
✅ Processing complete!
📊 Results: 12/45 relevant jobs (26.7%)
📄 Files saved to: processed_jobs/
```

---

## 🎯 Benefits

### ✅ Advantages

- **Fully automated**: No manual intervention needed
- **Cost-effective**: Only processes new jobs
- **Scalable**: Handles any number of jobs
- **Reliable**: GitHub Actions infrastructure
- **Trackable**: Complete job history
- **Efficient**: Deduplication prevents waste

### 🔄 Workflow Efficiency

- **Local scraping**: Lightweight, no overheating
- **Cloud processing**: Uses GitHub's resources
- **Smart tracking**: Avoids redundant processing
- **Automatic commits**: Seamless integration

---

## 🚀 Next Steps

1. **Set up the repository** following the instructions above
2. **Test the workflow** with a manual run
3. **Configure notifications** if desired
4. **Monitor results** and adjust parameters
5. **Scale up** by adding more job sources

**Happy automated job hunting! 🎉** 