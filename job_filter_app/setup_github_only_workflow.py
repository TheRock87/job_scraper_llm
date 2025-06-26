#!/usr/bin/env python3
"""
GitHub Actions Only Workflow Setup
Complete setup for GitHub Actions + Google Drive + Colab workflow
"""

import subprocess
import os
import sys
from pathlib import Path
import json

def check_git_status():
    """Check if we're in a git repository"""
    try:
        result = subprocess.run(["git", "status"], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def setup_git_repository():
    """Setup git repository"""
    print("🔧 Setting up Git repository...")
    
    if not check_git_status():
        print("📁 Initializing Git repository...")
        result = subprocess.run(["git", "init"], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Failed to initialize git: {result.stderr}")
            return False
        print("✅ Git repository initialized")
    
    # Setup main branch
    try:
        result = subprocess.run(["git", "branch", "-M", "main"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Main branch configured")
    except Exception as e:
        print(f"⚠️ Branch setup warning: {e}")
    
    return True

def setup_github_remote():
    """Setup GitHub remote"""
    print("\n🔗 Setting up GitHub remote...")
    
    try:
        # Check if remote exists
        result = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Remote origin already exists: {result.stdout.strip()}")
            return True
    except:
        pass
    
    # Ask for repository URL
    print("📝 Please provide your GitHub repository URL")
    print("   Example: https://github.com/username/jobspy-repo.git")
    repo_url = input("🔗 GitHub repository URL: ").strip()
    
    if not repo_url:
        print("⚠️ No repository URL provided")
        print("💡 You can add it later with:")
        print("   git remote add origin <your-repo-url>")
        return False
    
    # Add remote
    result = subprocess.run(["git", "remote", "add", "origin", repo_url], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"✅ Remote origin added: {repo_url}")
        return True
    else:
        print(f"❌ Failed to add remote: {result.stderr}")
        return False

def create_github_workflow_dir():
    """Create GitHub Actions workflow directory"""
    print("\n📁 Creating GitHub Actions directory...")
    
    workflow_dir = Path(".github/workflows")
    workflow_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"✅ Created directory: {workflow_dir}")
    return True

def setup_rclone():
    """Setup rclone for Google Drive"""
    print("\n☁️ Setting up rclone for Google Drive...")
    
    # Check if rclone is installed
    try:
        result = subprocess.run(["rclone", "version"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ rclone is already installed")
        else:
            print("📥 Installing rclone...")
            result = subprocess.run(["curl", "https://rclone.org/install.sh"], capture_output=True, text=True)
            if result.returncode != 0:
                print("❌ Failed to download rclone installer")
                return False
            
            # Note: User needs to run this manually
            print("⚠️ Please run the following command to install rclone:")
            print("   curl https://rclone.org/install.sh | sudo bash")
            return False
    except FileNotFoundError:
        print("📥 Installing rclone...")
        print("⚠️ Please run the following command to install rclone:")
        print("   curl https://rclone.org/install.sh | sudo bash")
        return False
    
    return True

def configure_google_drive():
    """Configure Google Drive with rclone"""
    print("\n🔧 Configuring Google Drive...")
    
    try:
        # Check if gdrive remote exists
        result = subprocess.run(["rclone", "listremotes"], capture_output=True, text=True)
        if result.returncode == 0 and "gdrive:" in result.stdout:
            print("✅ Google Drive is already configured")
            return True
        else:
            print("🔧 Setting up Google Drive configuration...")
            print("📝 Please run the following command to configure Google Drive:")
            print("   rclone config")
            print("\n📋 Configuration steps:")
            print("1. Choose 'n' for new remote")
            print("2. Name it 'gdrive'")
            print("3. Choose 'drive' (Google Drive)")
            print("4. Choose 'y' to use auto config")
            print("5. Follow browser authentication")
            print("6. Choose 'y' to configure as team drive (optional)")
            print("7. Choose '1' for full access")
            print("8. Choose 'y' to confirm")
            return False
    except Exception as e:
        print(f"❌ Error configuring Google Drive: {e}")
        return False

def create_ai_jobs_folder():
    """Create AI-Jobs folder in Google Drive"""
    print("\n📁 Creating AI-Jobs folder in Google Drive...")
    
    try:
        result = subprocess.run(["rclone", "mkdir", "gdrive:AI-Jobs"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ AI-Jobs folder created in Google Drive")
            return True
        else:
            print("⚠️ AI-Jobs folder might already exist or creation failed")
            return True  # Not critical
    except Exception as e:
        print(f"⚠️ Could not create AI-Jobs folder: {e}")
        return True  # Not critical

def export_rclone_config():
    """Export rclone configuration for GitHub Actions"""
    print("\n📤 Exporting rclone configuration...")
    
    try:
        result = subprocess.run(["rclone", "config", "show"], capture_output=True, text=True)
        if result.returncode == 0:
            config_content = result.stdout
            
            # Save to file
            with open("rclone_config.txt", "w") as f:
                f.write(config_content)
            
            print("✅ Rclone configuration exported to rclone_config.txt")
            print("📝 Next step: Add this configuration as GitHub secret 'RCLONE_CONFIG'")
            return True
        else:
            print("❌ Failed to export rclone configuration")
            return False
    except Exception as e:
        print(f"❌ Error exporting rclone config: {e}")
        return False

def create_sample_jobs_file():
    """Create a sample jobs file to trigger the workflow"""
    print("\n📄 Creating sample jobs file...")
    
    sample_jobs = [
        {
            "title": "AI Engineer",
            "company": "Sample Company",
            "location": "Cairo, Egypt",
            "job_url": "https://example.com/job1",
            "description": "Sample AI engineering position for testing",
            "search_term": "Ai engineer",
            "search_location": "Cairo, Egypt"
        },
        {
            "title": "Machine Learning Engineer",
            "company": "Test Corp",
            "location": "Dubai, UAE",
            "job_url": "https://example.com/job2",
            "description": "Sample ML engineering position for testing",
            "search_term": "Machine learning engineer",
            "search_location": "Dubai, UAE"
        }
    ]
    
    try:
        import pandas as pd
        df = pd.DataFrame(sample_jobs)
        df.to_csv("jobs_raw.csv", index=False)
        print("✅ Sample jobs_raw.csv created")
        return True
    except ImportError:
        print("⚠️ pandas not available, creating simple CSV")
        try:
            with open("jobs_raw.csv", "w") as f:
                f.write("title,company,location,job_url,description,search_term,search_location\n")
                f.write("AI Engineer,Sample Company,Cairo Egypt,https://example.com/job1,Sample AI engineering position,Ai engineer,Cairo Egypt\n")
                f.write("Machine Learning Engineer,Test Corp,Dubai UAE,https://example.com/job2,Sample ML engineering position,Machine learning engineer,Dubai UAE\n")
            print("✅ Sample jobs_raw.csv created")
            return True
        except Exception as e:
            print(f"❌ Failed to create sample file: {e}")
            return False

def initial_commit_and_push():
    """Make initial commit and push to GitHub"""
    print("\n📝 Making initial commit...")
    
    try:
        # Add all files
        result = subprocess.run(["git", "add", "."], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Failed to add files: {result.stderr}")
            return False
        
        # Commit
        result = subprocess.run(["git", "commit", "-m", "🚀 Initial setup - GitHub Actions + Google Drive workflow"], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Failed to commit: {result.stderr}")
            return False
        
        print("✅ Initial commit created")
        
        # Push to GitHub
        print("🚀 Pushing to GitHub...")
        result = subprocess.run(["git", "push", "-u", "origin", "main"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Successfully pushed to GitHub")
            return True
        else:
            print(f"❌ Failed to push: {result.stderr}")
            print("💡 You may need to:")
            print("   1. Create the repository on GitHub first")
            print("   2. Set up authentication (SSH key or token)")
            return False
            
    except Exception as e:
        print(f"❌ Error with commit/push: {e}")
        return False

def create_colab_notebook():
    """Create an updated Colab notebook for the GitHub workflow"""
    print("\n📱 Creating updated Colab notebook...")
    
    colab_content = """# 🤖 AI Job Processing - GitHub Actions + Google Drive

This notebook works with the GitHub Actions workflow that automatically processes jobs and uploads results to Google Drive.

## 🚀 Setup

```python
# Install required packages
!pip install -q transformers accelerate torch pandas tqdm
```

## ☁️ Mount Google Drive

```python
from google.colab import drive
drive.mount('/content/drive')

DRIVE_PATH = '/content/drive/MyDrive/AI-Jobs'
print(f"📁 Drive mounted at: {DRIVE_PATH}")
```

## 📊 Load Processed Jobs

```python
import pandas as pd
import os

# Choose which file to load:
# - processed_jobs.csv (jobs with AI classifications)
# - filtered_jobs.html (interactive table)
# - jobs_raw.csv (raw scraped jobs)

INPUT_FILE = 'processed_jobs.csv'  # Recommended
input_path = f"{DRIVE_PATH}/{INPUT_FILE}"

if os.path.exists(input_path):
    df = pd.read_csv(input_path)
    print(f"✅ Loaded {len(df)} jobs from {input_path}")
    
    # Show relevant jobs
    relevant_jobs = df[df['Is_Junior_AI_Job'] == 'Yes']
    print(f"🎯 Relevant jobs: {len(relevant_jobs)}")
    
    # Display sample
    display(relevant_jobs.head())
else:
    print(f"❌ File not found: {input_path}")
    print("💡 Make sure the GitHub Actions workflow has run and uploaded files")
```

## 🌐 View Interactive Results

```python
# If you have the HTML file, you can view it
HTML_FILE = 'filtered_jobs.html'
html_path = f"{DRIVE_PATH}/{HTML_FILE}"

if os.path.exists(html_path):
    from IPython.display import HTML
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    display(HTML(html_content))
else:
    print(f"❌ HTML file not found: {html_path}")
```

## 📈 View Processing Summary

```python
# Load processing summary
SUMMARY_FILE = 'processing_summary.json'
summary_path = f"{DRIVE_PATH}/{SUMMARY_FILE}"

if os.path.exists(summary_path):
    import json
    with open(summary_path, 'r') as f:
        summary = json.load(f)
    
    print("📊 Processing Summary:")
    print(f"  Total jobs: {summary.get('total_jobs', 0)}")
    print(f"  Relevant jobs: {summary.get('relevant_jobs', 0)}")
    print(f"  Relevance rate: {summary.get('relevance_rate', 0)}%")
    print(f"  Processed at: {summary.get('timestamp', 'Unknown')}")
else:
    print(f"❌ Summary file not found: {summary_path}")
```

## 🔄 Workflow

1. **GitHub Actions** automatically processes new jobs
2. **Results** are uploaded to Google Drive AI-Jobs folder
3. **This notebook** loads and displays the results
4. **No local processing** needed!

## 📝 Next Steps

- Check your GitHub repository Actions tab for workflow status
- Files will appear in Google Drive AI-Jobs folder after processing
- Run this notebook to view the latest results
"""
    
    try:
        with open("job_processing_colab_github.md", "w") as f:
            f.write(colab_content)
        print("✅ Updated Colab notebook created: job_processing_colab_github.md")
        return True
    except Exception as e:
        print(f"❌ Failed to create Colab notebook: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 GitHub Actions Only Workflow Setup")
    print("=" * 60)
    print("This will set up a complete GitHub Actions + Google Drive + Colab workflow")
    print("No local scraping needed - everything runs in the cloud!")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not Path("config_scraper.yaml").exists():
        print("❌ Please run this script from the job_filter_app directory")
        sys.exit(1)
    
    steps = [
        ("Git Repository", setup_git_repository),
        ("GitHub Remote", setup_github_remote),
        ("GitHub Actions Directory", create_github_workflow_dir),
        ("Rclone Installation", setup_rclone),
        ("Google Drive Configuration", configure_google_drive),
        ("AI-Jobs Folder", create_ai_jobs_folder),
        ("Rclone Config Export", export_rclone_config),
        ("Sample Jobs File", create_sample_jobs_file),
        ("Colab Notebook", create_colab_notebook),
    ]
    
    results = []
    for step_name, step_func in steps:
        print(f"\n📋 {step_name}...")
        try:
            result = step_func()
            results.append((step_name, result))
        except Exception as e:
            print(f"❌ {step_name} failed with exception: {e}")
            results.append((step_name, False))
    
    # Try to commit and push
    print(f"\n📋 Commit and Push...")
    commit_result = initial_commit_and_push()
    results.append(("Commit and Push", commit_result))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Setup Results:")
    
    passed = 0
    for step_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {step_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{len(results)} steps completed")
    
    if passed >= len(results) - 2:  # Allow some non-critical failures
        print("\n🎉 Setup mostly complete!")
        print("\n📝 Next steps:")
        print("1. Create GitHub repository (if not done)")
        print("2. Add RCLONE_CONFIG secret to GitHub repository:")
        print("   - Go to Settings → Secrets and variables → Actions")
        print("   - Add secret 'RCLONE_CONFIG' with content from rclone_config.txt")
        print("3. Push to GitHub: git push -u origin main")
        print("4. Check GitHub Actions tab for workflow runs")
        print("5. Open Colab notebook: job_processing_colab_github.md")
        print("6. Mount Google Drive and load results")
        
        print("\n📚 Files created:")
        print("- rclone_config.txt (add as GitHub secret)")
        print("- job_processing_colab_github.md (Colab notebook)")
        print("- jobs_raw.csv (sample file to trigger workflow)")
        
        print("\n🚀 Your workflow is ready!")
        print("💡 To trigger processing, just update jobs_raw.csv and push to GitHub")
    else:
        print("\n⚠️ Setup incomplete. Please fix the failed steps above.")
    
    return passed >= len(results) - 2

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️ Setup stopped by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 