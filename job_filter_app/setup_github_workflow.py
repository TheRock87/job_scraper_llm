#!/usr/bin/env python3
"""
GitHub Workflow Setup Script
Helps initialize the repository and configure GitHub Actions
"""

import subprocess
import os
import sys
from pathlib import Path

def check_git_status():
    """Check if we're in a git repository"""
    try:
        result = subprocess.run(["git", "status"], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def check_remote_exists():
    """Check if a remote origin exists"""
    try:
        result = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def setup_git_repository():
    """Setup git repository if not already done"""
    print("🔧 Setting up Git repository...")
    
    if not check_git_status():
        print("📁 Initializing Git repository...")
        result = subprocess.run(["git", "init"], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Failed to initialize git: {result.stderr}")
            return False
        print("✅ Git repository initialized")
    
    if not check_remote_exists():
        print("⚠️ No remote origin found")
        repo_url = input("🔗 Enter your GitHub repository URL (e.g., https://github.com/username/repo.git): ").strip()
        
        if repo_url:
            result = subprocess.run(["git", "remote", "add", "origin", repo_url], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ Failed to add remote: {result.stderr}")
                return False
            print(f"✅ Remote origin added: {repo_url}")
        else:
            print("⚠️ No repository URL provided. You'll need to add it manually:")
            print("   git remote add origin <your-repo-url>")
    
    return True

def create_github_workflow_dir():
    """Create the .github/workflows directory"""
    print("📁 Creating GitHub Actions directory...")
    
    workflow_dir = Path(".github/workflows")
    workflow_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"✅ Created directory: {workflow_dir}")
    return True

def check_workflow_file():
    """Check if the workflow file exists"""
    workflow_file = Path(".github/workflows/job_processing.yml")
    return workflow_file.exists()

def setup_branch():
    """Setup main branch"""
    print("🌿 Setting up main branch...")
    
    try:
        # Check current branch
        result = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True)
        current_branch = result.stdout.strip()
        
        if current_branch != "main":
            result = subprocess.run(["git", "branch", "-M", "main"], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ Failed to rename branch: {result.stderr}")
                return False
            print("✅ Branch renamed to 'main'")
        else:
            print("✅ Already on main branch")
        
        return True
    except Exception as e:
        print(f"❌ Error setting up branch: {e}")
        return False

def initial_commit():
    """Make initial commit if needed"""
    print("📝 Checking for initial commit...")
    
    try:
        # Check if there are any commits
        result = subprocess.run(["git", "log", "--oneline"], capture_output=True, text=True)
        if not result.stdout.strip():
            print("📝 Making initial commit...")
            
            # Add all files
            result = subprocess.run(["git", "add", "."], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ Failed to add files: {result.stderr}")
                return False
            
            # Commit
            result = subprocess.run(["git", "commit", "-m", "🚀 Initial commit - JobSpy with GitHub Actions"], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"❌ Failed to commit: {result.stderr}")
                return False
            
            print("✅ Initial commit created")
        else:
            print("✅ Repository already has commits")
        
        return True
    except Exception as e:
        print(f"❌ Error with initial commit: {e}")
        return False

def push_to_github():
    """Push to GitHub"""
    print("🚀 Pushing to GitHub...")
    
    try:
        result = subprocess.run(["git", "push", "-u", "origin", "main"], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Failed to push: {result.stderr}")
            print("💡 You may need to:")
            print("   1. Create the repository on GitHub first")
            print("   2. Set up authentication (SSH key or token)")
            return False
        
        print("✅ Successfully pushed to GitHub")
        return True
    except Exception as e:
        print(f"❌ Error pushing to GitHub: {e}")
        return False

def test_workflow():
    """Test the workflow setup"""
    print("\n🧪 Testing workflow setup...")
    
    # Test if we can run the workflow script
    try:
        result = subprocess.run([sys.executable, "github_actions_workflow.py", "--test"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Workflow script test passed")
        else:
            print("⚠️ Workflow script test failed")
    except Exception as e:
        print(f"⚠️ Could not test workflow script: {e}")

def main():
    """Main setup function"""
    print("🚀 GitHub Actions Workflow Setup")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("config_scraper.yaml").exists():
        print("❌ Please run this script from the job_filter_app directory")
        sys.exit(1)
    
    steps = [
        ("Git Repository", setup_git_repository),
        ("GitHub Workflow Directory", create_github_workflow_dir),
        ("Main Branch", setup_branch),
        ("Initial Commit", initial_commit),
    ]
    
    for step_name, step_func in steps:
        print(f"\n📋 {step_name}...")
        if not step_func():
            print(f"❌ {step_name} failed")
            sys.exit(1)
    
    # Check workflow file
    if not check_workflow_file():
        print("\n⚠️ Workflow file not found!")
        print("   Make sure .github/workflows/job_processing.yml exists")
        print("   This should have been created by the main setup")
    
    # Test workflow
    test_workflow()
    
    # Push to GitHub
    print(f"\n📋 Push to GitHub...")
    push_success = push_to_github()
    
    # Final instructions
    print("\n" + "=" * 50)
    print("🎉 Setup Complete!")
    print("=" * 50)
    
    if push_success:
        print("✅ Repository is ready for GitHub Actions!")
        print("\n📝 Next steps:")
        print("1. Go to your GitHub repository")
        print("2. Check the Actions tab")
        print("3. Run the scraper: python scraper_with_git.py")
        print("4. Watch the workflow run automatically!")
    else:
        print("⚠️ Setup complete, but push to GitHub failed")
        print("\n📝 Manual steps needed:")
        print("1. Create repository on GitHub")
        print("2. Run: git push -u origin main")
        print("3. Enable GitHub Actions in repository settings")
    
    print("\n📚 For more information, see README_GITHUB_ACTIONS.md")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️ Setup stopped by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 