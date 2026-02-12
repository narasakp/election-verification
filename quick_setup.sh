#!/bin/bash

# ========================================
# Quick Setup Script
# ระบบตรวจสอบการเลือกตั้ง 2026
# ========================================

set -e  # Exit on error

echo "========================================"
echo "🗳️  Election Verification System Setup"
echo "========================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ========================================
# Step 1: Check Prerequisites
# ========================================

echo "📋 Step 1: Checking prerequisites..."
echo ""

# Check Git
if ! command -v git &> /dev/null; then
    echo -e "${RED}❌ Git is not installed${NC}"
    echo "Please install Git first: https://git-scm.com/"
    exit 1
fi
echo -e "${GREEN}✓${NC} Git found: $(git --version)"

# Check Python (optional)
if command -v python3 &> /dev/null; then
    echo -e "${GREEN}✓${NC} Python found: $(python3 --version)"
else
    echo -e "${YELLOW}⚠${NC}  Python not found (optional, needed for data processing)"
fi

echo ""

# ========================================
# Step 2: Get GitHub Username
# ========================================

echo "📝 Step 2: GitHub Configuration"
echo ""

read -p "Enter your GitHub username: " GITHUB_USERNAME

if [ -z "$GITHUB_USERNAME" ]; then
    echo -e "${RED}❌ GitHub username is required${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} GitHub username: $GITHUB_USERNAME"
echo ""

# ========================================
# Step 3: Create Project Structure
# ========================================

echo "📁 Step 3: Creating project structure..."
echo ""

PROJECT_NAME="election-verification"

# Create main directory
mkdir -p $PROJECT_NAME
cd $PROJECT_NAME

# Create subdirectories
mkdir -p data
mkdir -p docs
mkdir -p scripts
mkdir -p assets
mkdir -p .github/workflows

echo -e "${GREEN}✓${NC} Created: $PROJECT_NAME/"
echo -e "${GREEN}✓${NC} Created: data/"
echo -e "${GREEN}✓${NC} Created: docs/"
echo -e "${GREEN}✓${NC} Created: scripts/"
echo -e "${GREEN}✓${NC} Created: assets/"
echo ""

# ========================================
# Step 4: Copy Files (User needs to do this)
# ========================================

echo "📂 Step 4: File Organization"
echo ""
echo -e "${YELLOW}⚠${NC}  Please copy files to the following locations:"
echo ""
echo "Root directory ($(pwd)):"
echo "  - github_pages_dashboard.html → index.html"
echo "  - PROJECT_README.md → README.md"
echo ""
echo "data/:"
echo "  - election_data_sample.json → data/election_data.json"
echo ""
echo "docs/:"
echo "  - GITHUB_PAGES_DEPLOYMENT.md → docs/DEPLOYMENT.md"
echo "  - VOTE62_COMPARISON_GUIDE.md → docs/COMPARISON_GUIDE.md"
echo ""
echo "scripts/:"
echo "  - election_verification_system.py → scripts/"
echo "  - vote62_comparator.py → scripts/"
echo "  - advanced_analytics.py → scripts/"
echo "  - examples.py → scripts/"
echo "  - generate_json_data.py → scripts/"
echo ""

read -p "Press Enter when you've copied all files..."

# ========================================
# Step 5: Create .gitignore
# ========================================

echo ""
echo "📝 Step 5: Creating .gitignore..."
echo ""

cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log

# Temporary files
*.tmp
*.bak
EOF

echo -e "${GREEN}✓${NC} Created .gitignore"
echo ""

# ========================================
# Step 6: Create GitHub Actions Workflow
# ========================================

echo "⚙️  Step 6: Creating GitHub Actions workflow..."
echo ""

cat > .github/workflows/update-data.yml << 'EOF'
name: Auto Update Election Data

on:
  schedule:
    # Run every hour
    - cron: '0 * * * *'
  workflow_dispatch:  # Allow manual trigger

jobs:
  update:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout repository
      uses: actions/checkout@v3
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install requests pandas numpy scipy
    
    - name: Update data
      run: |
        cd scripts
        python generate_json_data.py || echo "Script execution completed with warnings"
    
    - name: Commit and push if changed
      run: |
        git config --global user.name 'GitHub Actions Bot'
        git config --global user.email 'actions@github.com'
        git add data/election_data.json || echo "No data file to add"
        git diff --quiet && git diff --staged --quiet || \
        (git commit -m "🤖 Auto-update: $(date '+%Y-%m-%d %H:%M')" && git push)
EOF

echo -e "${GREEN}✓${NC} Created GitHub Actions workflow"
echo ""

# ========================================
# Step 7: Initialize Git Repository
# ========================================

echo "🔧 Step 7: Initializing Git repository..."
echo ""

git init
git branch -M main

echo -e "${GREEN}✓${NC} Git repository initialized"
echo ""

# ========================================
# Step 8: Add Remote Repository
# ========================================

echo "🔗 Step 8: Adding remote repository..."
echo ""

REPO_URL="https://github.com/$GITHUB_USERNAME/$PROJECT_NAME.git"
git remote add origin $REPO_URL

echo -e "${GREEN}✓${NC} Remote added: $REPO_URL"
echo ""

# ========================================
# Step 9: Initial Commit
# ========================================

echo "💾 Step 9: Creating initial commit..."
echo ""

git add .

git commit -m "🎉 Initial commit: Election Verification Dashboard

- Add interactive dashboard with Chart.js and Leaflet
- Add Vote62 comparison system
- Add statistical analysis tools
- Add comprehensive documentation
- Ready for GitHub Pages deployment

#นับใหม่ทั้งประเทศ #ระบอบหน้าด้าน"

echo -e "${GREEN}✓${NC} Initial commit created"
echo ""

# ========================================
# Step 10: Instructions for GitHub
# ========================================

echo "========================================"
echo "✅ Setup Complete!"
echo "========================================"
echo ""
echo "📝 Next Steps:"
echo ""
echo "1️⃣  Create GitHub repository:"
echo "   Go to: https://github.com/new"
echo "   Repository name: $PROJECT_NAME"
echo "   Make it Public"
echo "   Do NOT initialize with README"
echo ""
echo "2️⃣  Push to GitHub:"
echo "   git push -u origin main"
echo ""
echo "3️⃣  Enable GitHub Pages:"
echo "   Go to: https://github.com/$GITHUB_USERNAME/$PROJECT_NAME/settings/pages"
echo "   Source: Deploy from branch"
echo "   Branch: main, folder: / (root)"
echo "   Click Save"
echo ""
echo "4️⃣  Wait 1-2 minutes, then visit:"
echo "   https://$GITHUB_USERNAME.github.io/$PROJECT_NAME/"
echo ""
echo "========================================"
echo "🎊 Your site will be live soon!"
echo "========================================"
echo ""
echo "📚 Documentation:"
echo "   - README.md - Project overview"
echo "   - docs/DEPLOYMENT.md - Deployment guide"
echo "   - docs/COMPARISON_GUIDE.md - Usage guide"
echo ""
echo "💡 Tips:"
echo "   - Test locally first: python -m http.server 8000"
echo "   - Check console (F12) for errors"
echo "   - Update data: cd scripts && python generate_json_data.py"
echo ""
echo "🆘 Need help?"
echo "   - Check docs/DEPLOYMENT.md"
echo "   - Open GitHub issue"
echo "   - Visit Vote62.com"
echo ""
echo "========================================"
echo "Happy verifying! 🗳️"
echo "========================================"
