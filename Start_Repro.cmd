@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Create the Python virtual environment using README.md first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m scripts.run_local --open
pause
