@echo off
cd /d "c:\Lokal_Code\NewsAnalysis_3.0"
call venv\Scripts\activate.bat
python -m newsanalysis.cli.main run
