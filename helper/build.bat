@echo off
REM Builds ClientTrackerHelper.exe from this folder. Run after `pip install -r requirements.txt`
REM inside the venv. Output: dist\ClientTrackerHelper.exe (single file, no console window).
call venv\Scripts\activate
pyinstaller ClientTrackerHelper.spec
echo.
echo Done. Give dist\ClientTrackerHelper.exe to a worker's machine and double-click it to run.
