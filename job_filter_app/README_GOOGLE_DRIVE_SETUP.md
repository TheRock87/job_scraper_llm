# ☁️ Google Drive Integration Setup

This guide explains how to set up Google Drive integration for both local scraping and GitHub Actions workflows.

## 📋 Overview

The system now supports:
- **Local scraping** → Upload to Google Drive → Colab processing
- **GitHub Actions** → Process jobs → Upload results to Google Drive
- **Dual workflow** support for maximum flexibility

---

## 🛠️ Local Setup (for Colab Processing)

### Step 1: Install rclone

```bash
# Install rclone
curl https://rclone.org/install.sh | sudo bash

# Verify installation
rclone version
```

### Step 2: Configure Google Drive

```bash
# Start rclone configuration
rclone config

# Follow the prompts:
# 1. Choose "n" for new remote
# 2. Name it "gdrive"
# 3. Choose "drive" (Google Drive)
# 4. Choose "y" to use auto config
# 5. Follow browser authentication
# 6. Choose "y" to configure as team drive (optional)
# 7. Choose "1" for full access
# 8. Choose "y" to confirm
```

### Step 3: Test the Configuration

```bash
# List your Google Drive contents
rclone lsd gdrive:

# Create the AI-Jobs folder
rclone mkdir gdrive:AI-Jobs

# Test upload
echo "test" > test.txt
rclone copy test.txt gdrive:AI-Jobs/
rm test.txt
```

### Step 4: Use the Enhanced Scraper

```bash
# Run the scraper with Google Drive upload
python scraper_with_git.py
```

This will:
1. Scrape jobs
2. Save to `jobs_raw.csv`
3. Upload to `gdrive:AI-Jobs/`
4. Commit to Git (if available)

---

## 🚀 GitHub Actions Setup (for Automated Processing)

### Step 1: Get rclone Configuration

Export your rclone configuration:

```bash
# Export your rclone config
rclone config show > rclone_config.txt

# Or get just the gdrive section
rclone config show | grep -A 50 "\[gdrive\]" > rclone_gdrive_config.txt
```

### Step 2: Add GitHub Secrets

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add the following secrets:

#### Secret: `RCLONE_CONFIG`
- **Name**: `RCLONE_CONFIG`
- **Value**: Your complete rclone configuration (from `rclone config show`)

Example value:
```
[gdrive]
type = drive
client_id = your_client_id
client_secret = your_client_secret
token = your_token
refresh_token = your_refresh_token
```

### Step 3: Test GitHub Actions

1. Push a change to trigger the workflow
2. Check the Actions tab
3. Verify files are uploaded to Google Drive

---

## 📱 Colab Notebook Setup

### Updated Colab Workflow

Your Colab notebook can now work with files from Google Drive:

```python
# Mount Google Drive
from google.colab import drive
drive.mount('/content/drive')

# Define paths
DRIVE_PATH = '/content/drive/MyDrive/AI-Jobs'
INPUT_FILE = 'jobs_raw.csv'  # From local scraper
# OR
INPUT_FILE = 'processed_jobs.csv'  # From GitHub Actions

# Load jobs
input_path = f"{DRIVE_PATH}/{INPUT_FILE}"
df = pd.read_csv(input_path)
```

### Available Files in Google Drive

After running the workflows, you'll have:

1. **`jobs_raw.csv`** - Raw scraped jobs (from local scraper)
2. **`processed_jobs.csv`** - Jobs with AI classifications (from GitHub Actions)
3. **`filtered_jobs.html`** - Interactive job table (from GitHub Actions)
4. **`processing_summary.json`** - Processing statistics (from GitHub Actions)

---

## 🔄 Workflow Options

### Option 1: Local Scraping + Colab Processing
```bash
# 1. Run local scraper
python scraper_with_git.py

# 2. Open Colab notebook
# 3. Load jobs_raw.csv from Google Drive
# 4. Process with Mistral-7B
```

### Option 2: GitHub Actions Automated Processing
```bash
# 1. Run local scraper (triggers GitHub Actions)
python scraper_with_git.py

# 2. GitHub Actions automatically:
#    - Processes jobs with AI
#    - Uploads results to Google Drive
#    - Creates HTML output

# 3. Open Colab notebook
# 4. Load processed_jobs.csv or filtered_jobs.html
```

### Option 3: Hybrid Approach
- Use local scraping for immediate results
- Use GitHub Actions for comprehensive processing
- Access both outputs from Google Drive

---

## 🔧 Configuration

### Local Configuration (`config_scraper.yaml`)

```yaml
# Add Google Drive settings
gdrive_folder: gdrive:AI-Jobs
upload_to_gdrive: true
```

### GitHub Actions Configuration

The workflow automatically:
- Installs rclone
- Uses secrets for authentication
- Uploads to the configured folder

---

## 🛠️ Troubleshooting

### Local Issues

1. **rclone not found**:
   ```bash
   curl https://rclone.org/install.sh | sudo bash
   ```

2. **Authentication failed**:
   ```bash
   rclone config
   # Reconfigure the gdrive remote
   ```

3. **Permission denied**:
   ```bash
   # Check folder permissions
   rclone lsd gdrive:
   # Create folder if needed
   rclone mkdir gdrive:AI-Jobs
   ```

### GitHub Actions Issues

1. **RCLONE_CONFIG secret missing**:
   - Add the secret in repository settings
   - Use `rclone config show` output

2. **Authentication failed in Actions**:
   - Check token expiration
   - Regenerate tokens if needed

3. **Upload failures**:
   - Check folder permissions
   - Verify secret format

### Colab Issues

1. **Drive not mounted**:
   ```python
   from google.colab import drive
   drive.mount('/content/drive')
   ```

2. **File not found**:
   - Check file path
   - Verify file exists in Drive
   - Check folder structure

---

## 📊 File Structure in Google Drive

```
AI-Jobs/
├── jobs_raw.csv              # Raw scraped jobs
├── processed_jobs.csv        # Jobs with AI classifications
├── filtered_jobs.html        # Interactive job table
├── processing_summary.json   # Processing statistics
└── job_history.json         # Job tracking database
```

---

## 🎯 Benefits

### ✅ Advantages

- **Dual workflow support**: Local + GitHub Actions
- **Cloud storage**: Access files from anywhere
- **Colab integration**: Direct access from notebooks
- **Automated uploads**: No manual file management
- **Backup**: Files stored in Google Drive
- **Sharing**: Easy to share results with others

### 🔄 Workflow Flexibility

- **Local processing**: Immediate results
- **Cloud processing**: Comprehensive analysis
- **Hybrid approach**: Best of both worlds

---

## 🚀 Quick Start

1. **Setup rclone**:
   ```bash
   curl https://rclone.org/install.sh | sudo bash
   rclone config
   ```

2. **Test upload**:
   ```bash
   echo "test" > test.txt
   rclone copy test.txt gdrive:AI-Jobs/
   ```

3. **Run scraper**:
   ```bash
   python scraper_with_git.py
   ```

4. **Open Colab**:
   - Mount Google Drive
   - Load files from AI-Jobs folder
   - Process with your notebook

**Happy cloud-based job processing! ☁️🚀** 