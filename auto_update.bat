@echo off
:: Vietnam Stock Trader - Auto Update Script
:: Runs portfolio tracker and pushes updates to GitHub

cd /d "C:\Users\van\Documents\Projects\vietnam-stock-trader"

:: Set UTF-8
chcp 65001 > nul

:: Log start
echo [%date% %time%] Starting portfolio update >> logs\scheduler.log

:: Activate venv and run tracker
call backend\venv\Scripts\activate.bat
python portfolio_tracker.py >> logs\scheduler.log 2>&1

:: Push updates to GitHub (main branch)
git add portfolio_data.json dashboard\public\portfolio.html >> logs\scheduler.log 2>&1
git commit -m "Auto-update: Portfolio refresh %date% %time%" >> logs\scheduler.log 2>&1
git push >> logs\scheduler.log 2>&1

:: Update gh-pages branch for GitHub Pages
git stash >> logs\scheduler.log 2>&1
git checkout gh-pages >> logs\scheduler.log 2>&1
git show main:dashboard/public/portfolio.html > portfolio.html
git add portfolio.html >> logs\scheduler.log 2>&1
git commit -m "Auto-update: Portfolio %date% %time%" >> logs\scheduler.log 2>&1
git push origin gh-pages >> logs\scheduler.log 2>&1
git checkout main >> logs\scheduler.log 2>&1
git stash pop >> logs\scheduler.log 2>&1

:: Log end
echo [%date% %time%] Update complete >> logs\scheduler.log
echo. >> logs\scheduler.log
