# 🤖 JobSpy - Separated Workflow

This project has been restructured to separate job scraping (local) from LLM processing (Google Colab) to prevent laptop overheating issues.

## 📋 New Workflow Overview

### 🖥️ PART 1: LOCAL SCRAPING
- **Purpose**: Scrape job listings from multiple sources
- **Output**: `jobs_raw.csv` saved locally and uploaded to Google Drive
- **Automation**: Runs via cron job on Linux startup
- **No LLM**: Removes all AI processing to prevent overheating

### ☁️ PART 2: GOOGLE COLAB PROCESSING
- **Purpose**: Process scraped jobs with Mistral-7B model
- **Input**: `jobs_raw.csv` from Google Drive
- **Output**: `filtered_jobs.html` with interactive table
- **Benefits**: Uses Google's GPU resources, no local overheating

---

## 🚀 Quick Start

### Step 1: Setup Local Scraping

1. **Install dependencies**:
   ```bash
   cd job_filter_app
   pip install -r requirements.txt
   ```

2. **Configure scraping** (edit `config_scraper.yaml`):
   ```yaml
   search_term: '"Ai engineer" OR "Machine learning engineer" OR "Data scientist"'
   results_wanted: 30
   locations:
     - Cairo, Egypt
     - Dubai, UAE
   ```

3. **Setup rclone** (for Google Drive upload):
   ```bash
   # Install rclone
   curl https://rclone.org/install.sh | sudo bash
   
   # Configure Google Drive
   rclone config
   # Follow prompts to setup 'gdrive' remote
   ```

4. **Setup automatic scraping**:
   ```bash
   python3 setup_cron.py install
   ```

5. **Test scraping manually**:
   ```bash
   python3 scraper_only.py
   ```

### Step 2: Setup Google Colab Processing

1. **Open the notebook**:
   - Upload `job_filtering_colab.ipynb` to Google Colab
   - Or open directly from your Google Drive

2. **Run the notebook**:
   - Mount Google Drive
   - Load `jobs_raw.csv`
   - Process with Mistral-7B
   - Download `filtered_jobs.html`

---

## 📁 File Structure

```
job_filter_app/
├── scraper_only.py              # Local scraping script
├── config_scraper.yaml          # Scraping configuration
├── setup_cron.py               # Cron job setup
├── job_filtering_colab.ipynb   # Google Colab notebook
├── jobs_raw.csv                # Raw scraped jobs (generated)
├── filtered_jobs.html          # Processed results (generated)
└── scraper.log                 # Scraping logs (generated)
```

---

## ⚙️ Configuration

### Local Scraping Config (`config_scraper.yaml`)

```yaml
# Search configuration
search_term: '"Ai engineer" OR "Machine learning engineer" OR "Data scientist"'
results_wanted: 30
hours_old: 336  # 14 days

# Job sites
site_name:
  - linkedin
  - indeed

# Locations
locations:
  - Cairo, Egypt
  - Dubai, UAE

# Output settings
output_file: jobs_raw.csv
gdrive_folder: gdrive:AI-Jobs

# Automation
cron_schedule: "0 8 * * *"  # Daily at 8 AM
```

### Google Colab Settings

The notebook automatically:
- Uses Mistral-7B-Instruct-v0.2 model
- Applies 8-bit quantization for memory efficiency
- Uses the same prompt template as your original config
- Creates interactive HTML output

---

## 🔧 Automation Setup

### Cron Job Management

```bash
# Install cron job (runs daily at 8 AM)
python3 setup_cron.py install

# Check current cron jobs
python3 setup_cron.py status

# Remove cron job
python3 setup_cron.py remove
```

### Manual Execution

```bash
# Run scraping manually
python3 scraper_only.py

# Check logs
tail -f scraper.log
```

---

## 📊 Output Files

### `jobs_raw.csv`
- Raw scraped job data
- Contains: title, company, location, description, URL, etc.
- Uploaded to Google Drive automatically

### `filtered_jobs.html`
- Interactive web table
- Features:
  - ✅ Sortable columns
  - 🔍 Search functionality
  - 🔗 Clickable job URLs
  - 📊 Statistics dashboard
  - 📱 Responsive design

### `jobs_processed_YYYYMMDD_HHMMSS.csv`
- Processed data with AI classifications
- Contains: original data + `Is_Junior_AI_Job` column

---

## 🛠️ Troubleshooting

### Local Scraping Issues

1. **rclone not found**:
   ```bash
   curl https://rclone.org/install.sh | sudo bash
   rclone config
   ```

2. **Permission denied**:
   ```bash
   chmod +x scraper_only.py
   chmod +x setup_cron.py
   ```

3. **Import errors**:
   ```bash
   pip install -r requirements.txt
   ```

### Google Colab Issues

1. **Drive not mounted**:
   - Run the mount cell again
   - Check file permissions

2. **Model loading errors**:
   - Restart runtime
   - Use GPU runtime type

3. **Memory issues**:
   - Model uses 8-bit quantization
   - Close other notebooks

---

## 🔄 Workflow Automation

### Daily Process

1. **8:00 AM**: Cron job runs scraping
2. **8:05 AM**: `jobs_raw.csv` uploaded to Drive
3. **Manual**: Run Colab notebook when convenient
4. **Result**: Fresh `filtered_jobs.html` available

### Manual Trigger

```bash
# Force run scraping
python3 scraper_only.py

# Then run Colab notebook manually
```

---

## 📈 Benefits of New Workflow

### ✅ Advantages
- **No overheating**: LLM processing moved to cloud
- **Reliable**: Local scraping is lightweight
- **Scalable**: Can increase scraping frequency
- **Cost-effective**: Uses free Google Colab GPU
- **Automated**: Minimal manual intervention needed

### 🔧 Customization Options
- **Scraping frequency**: Modify cron schedule
- **Search terms**: Edit `config_scraper.yaml`
- **Model**: Change in Colab notebook
- **Output format**: Modify HTML template

---

## 🆘 Support

### Common Questions

**Q: Can I change the scraping schedule?**
A: Yes, edit `cron_schedule` in `config_scraper.yaml`

**Q: How do I add new job sites?**
A: Add to `site_name` list in config (check jobspy documentation)

**Q: Can I use a different AI model?**
A: Yes, modify the model name in the Colab notebook

**Q: How do I backup my data?**
A: Files are automatically saved to Google Drive

### Getting Help

1. Check `scraper.log` for local errors
2. Review Colab notebook output for processing errors
3. Verify rclone configuration
4. Test with manual execution first

---

## 🎯 Next Steps

1. **Setup the workflow** following the Quick Start guide
2. **Test manually** before enabling automation
3. **Customize** search terms and locations as needed
4. **Monitor** logs and results
5. **Optimize** based on your needs

**Happy job hunting! 🚀** 