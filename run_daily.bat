@echo off
cd /d "c:\Lokal_Code\NewsAnalysis_3.0"

REM Pre-Check: TCP-Connect zum DB-Server (Port 1433, MSSQL).
REM Ohne diesen Pfad funktioniert weder Crediweb-Lookup noch der Outlook-Mailversand
REM mit der Creditreform-Adresse. Funktioniert sowohl im internen Netz als auch ueber VPN.
echo Pruefe Verbindung zum DB-Server prodsvcreport.svc.ch:1433 ...
powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; if (Test-NetConnection -ComputerName prodsvcreport.svc.ch -Port 1433 -InformationLevel Quiet -WarningAction SilentlyContinue) { exit 0 } else { exit 1 }"
if errorlevel 1 (
    echo.
    echo ============================================================
    echo  FEHLER: prodsvcreport.svc.ch:1433 nicht erreichbar.
    echo  Bitte pruefen:
    echo    - Im Home Office: VPN verbinden
    echo    - Im Buero: Netzwerk-Verbindung pruefen
    echo  Anschliessend Skript erneut doppelklicken.
    echo ============================================================
    echo.
    exit /b 1
)
echo Verbindung OK.
echo.

call venv\Scripts\activate.bat
pip install -e . -q
python -m newsanalysis.cli.main run
echo.
echo === Pipeline beendet ===
