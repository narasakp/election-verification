@echo off
REM ========================================
REM Quick Setup Script for Windows
REM Election Verification System 2026
REM ========================================

echo ========================================
echo 🗳️  Election Verification System Setup
echo ========================================
echo.

REM ========================================
REM Step 1: Check Git
REM ========================================

echo 📋 Step 1: Checking prerequisites...
echo.

where git >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Git is not installed
    echo Please install Git first: https://git-scm.com/
    pause
    exit /b 1
)
echo ✓ Git found
echo.

REM ========================================
REM Step 2: Get GitHub Username
REM ========================================

echo 📝 Step 2: GitHub Configuration
echo.

set /p GITHUB_USERNAME="Enter your GitHub username: "

if "%GITHUB_USERNAME%"=="" (
    echo ❌ GitHub username is required
    pause
    exit /b 1
)

echo ✓ GitHub username: %GITHUB_USERNAME%
echo.

REM ========================================
REM Step 3: Create Project Structure
REM ========================================

echo 📁 Step 3: Creating project structure...
echo.

set PROJECT_NAME=election-verification

REM Create directories
mkdir %PROJECT_NAME%
cd %PROJECT_NAME%

mkdir data
mkdir docs
mkdir scripts
mkdir assets
mkdir .github
mkdir .github\workflows

echo ✓ Created: %PROJECT_NAME%\
echo ✓ Created: data\
echo ✓ Created: docs\
echo ✓ Created: scripts\
echo ✓ Created: assets\
echo.

REM ========================================
REM Step 4: Instructions
REM ========================================

echo 📂 Step 4: File Organization
echo.
echo ⚠  Please copy files to the following locations:
echo.
echo Root directory (%CD%):
echo   - github_pages_dashboard.html → index.html
echo   - PROJECT_README.md → README.md
echo.
echo data\:
echo   - election_data_sample.json → data\election_data.json
echo.
echo docs\:
echo   - GITHUB_PAGES_DEPLOYMENT.md → docs\DEPLOYMENT.md
echo   - VOTE62_COMPARISON_GUIDE.md → docs\COMPARISON_GUIDE.md
echo.
echo scripts\:
echo   - All Python files → scripts\
echo.

pause

REM ========================================
REM Step 5: Create .gitignore
REM ========================================

echo.
echo 📝 Step 5: Creating .gitignore...
echo.

(
echo # Python
echo __pycache__/
echo *.py[cod]
echo *$py.class
echo *.so
echo .Python
echo venv/
echo env/
echo.
echo # IDE
echo .vscode/
echo .idea/
echo *.swp
echo.
echo # OS
echo .DS_Store
echo Thumbs.db
echo.
echo # Logs
echo *.log
) > .gitignore

echo ✓ Created .gitignore
echo.

REM ========================================
REM Step 6: Create GitHub Actions
REM ========================================

echo ⚙️  Step 6: Creating GitHub Actions workflow...
echo.

(
echo name: Auto Update Election Data
echo.
echo on:
echo   schedule:
echo     - cron: '0 * * * *'
echo   workflow_dispatch:
echo.
echo jobs:
echo   update:
echo     runs-on: ubuntu-latest
echo     steps:
echo     - uses: actions/checkout@v3
echo     - uses: actions/setup-python@v4
echo       with:
echo         python-version: '3.11'
echo     - run: pip install requests pandas numpy scipy
echo     - run: cd scripts ^&^& python generate_json_data.py
echo     - run: ^|
echo         git config --global user.name 'GitHub Actions Bot'
echo         git config --global user.email 'actions@github.com'
echo         git add data/election_data.json
echo         git commit -m "Auto-update" ^&^& git push ^|^| echo "No changes"
) > .github\workflows\update-data.yml

echo ✓ Created GitHub Actions workflow
echo.

REM ========================================
REM Step 7: Initialize Git
REM ========================================

echo 🔧 Step 7: Initializing Git repository...
echo.

git init
git branch -M main

echo ✓ Git repository initialized
echo.

REM ========================================
REM Step 8: Add Remote
REM ========================================

echo 🔗 Step 8: Adding remote repository...
echo.

set REPO_URL=https://github.com/%GITHUB_USERNAME%/%PROJECT_NAME%.git
git remote add origin %REPO_URL%

echo ✓ Remote added: %REPO_URL%
echo.

REM ========================================
REM Step 9: Initial Commit
REM ========================================

echo 💾 Step 9: Creating initial commit...
echo.

git add .
git commit -m "Initial commit: Election Verification Dashboard"

echo ✓ Initial commit created
echo.

REM ========================================
REM Step 10: Final Instructions
REM ========================================

echo ========================================
echo ✅ Setup Complete!
echo ========================================
echo.
echo 📝 Next Steps:
echo.
echo 1️⃣  Create GitHub repository:
echo    Go to: https://github.com/new
echo    Repository name: %PROJECT_NAME%
echo    Make it Public
echo.
echo 2️⃣  Push to GitHub:
echo    git push -u origin main
echo.
echo 3️⃣  Enable GitHub Pages:
echo    Settings → Pages → Deploy from branch: main
echo.
echo 4️⃣  Visit your site:
echo    https://%GITHUB_USERNAME%.github.io/%PROJECT_NAME%/
echo.
echo ========================================
echo 🎊 Your site will be live soon!
echo ========================================
echo.

pause
