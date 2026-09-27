@echo off
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python 3 is required. Install Python 3 from python.org and enable Add Python to PATH.
  pause
  exit /b 1
)
py -c "import coinbase" >nul 2>nul
if errorlevel 1 (
  py -m pip install --user --upgrade coinbase-advanced-py
  if errorlevel 1 (echo Coinbase SDK installation failed.&pause&exit /b 1)
)
rem Optional sleek UI theme package. Safe to fail offline/blocked -- the app
rem falls back automatically to its built-in Dark/Light/Midnight Blue themes.
py -c "import ttkbootstrap" >nul 2>nul
if errorlevel 1 (
  py -m pip install --user --upgrade ttkbootstrap >nul 2>nul
)
start "" pyw "%~dp0CoinbaseBTCMakerBot.py"
