@echo off
cd /d "c:\Lokal_Code\NewsAnalysis_3.0"
call venv\Scripts\activate.bat
pip install -e . -q
python -m newsanalysis.cli.main run
echo.
echo === Pipeline beendet — Mails liegen im Outlook-Entwurfsordner ===
echo Druecke eine Taste zum Schliessen.
pause >nul
