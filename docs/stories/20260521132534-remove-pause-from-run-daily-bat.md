# Remove `pause` from run_daily.bat to unblock Scheduler-Trigger

## Summary

Die beiden `pause >nul`-Aufrufe in `run_daily.bat` werden entfernt. Sie liessen das `cmd.exe`-Fenster nach Pipeline-Ende offen, wodurch der Windows Task Scheduler die gestartete Instanz nie als beendet sah und alle folgenden Trigger mit Event-ID 322 (`already running`) verwarf.

## Context / Problem

Am 19.05.2026 12:30 lief der geplante Task `NewsAnalysis Daily Run` erfolgreich durch und schickte das Mail. Das `cmd.exe`-Fenster blieb wegen `pause >nul` am Skript-Ende offen und wurde nicht geschlossen. Aus Sicht des Task-Schedulers war die Instanz `{6d565925-33f6-419c-bebb-4810ad01cd18}` damit weiterhin im Zustand `Running`.

Mit `MultipleInstances=IgnoreNew` im Task-Setting verwarf der Scheduler beide nachfolgenden Trigger:

- 20.05.2026 12:30 — Event-ID 322 (`did not launch ... already running`)
- 21.05.2026 12:30 — Event-ID 322 (`did not launch ... already running`), `LastTaskResult=0x800710E0`

An beiden Tagen wurden somit weder Artikel gesammelt noch Mails versandt — obwohl der Rechner lief.

Der `pause` war mit Commit `f64b63b` ("chore: pause am Ende von run_daily.bat fuer Doppelklick-Workflow") eingeführt worden, damit beim Doppelklick-Start die Pipeline-Ausgabe sichtbar bleibt. Der Nutzen ist gering, weil sämtliche Pipeline-Events ohnehin im JSON-Log unter `logs/newsanalysis.log` persistiert werden; das Risiko (Phantom-Instanz blockiert alle Scheduler-Trigger) ist hoch.

## What Changed

- `run_daily.bat`: beide `pause >nul`-Aufrufe entfernt — am Ende des Skripts sowie im DB-Fehlerpfad. Skript läuft jetzt im Doppelklick- wie im Scheduler-Lauf bis zum Exit durch.
- `pyproject.toml`: Version auf `3.8.2` gebumpt.

## How to Test

1. Phantom-Instanz im Task Scheduler beenden:
   ```powershell
   Stop-ScheduledTask -TaskName "NewsAnalysis Daily Run"
   (Get-ScheduledTaskInfo -TaskName "NewsAnalysis Daily Run").State   # erwartet: Ready
   ```
2. Task manuell anstossen:
   ```powershell
   Start-ScheduledTask -TaskName "NewsAnalysis Daily Run"
   ```
3. Nach Abschluss prüfen, dass keine `cmd.exe`/`python.exe`-Prozesse der Task-Instanz übrig sind und der Task-State wieder `Ready` ist:
   ```powershell
   (Get-ScheduledTaskInfo -TaskName "NewsAnalysis Daily Run") | Format-List State, LastRunTime, LastTaskResult, NextRunTime
   ```
4. Eventlog kontrollieren, dass eine `201`-Information (`successfully completed`) eingetragen wurde:
   ```powershell
   Get-WinEvent -LogName 'Microsoft-Windows-TaskScheduler/Operational' -MaxEvents 50 |
     Where-Object Message -match 'NewsAnalysis' | Select-Object TimeCreated, Id, LevelDisplayName
   ```

## Risk / Rollback Notes

- **Risiko**: Beim manuellen Doppelklick verschwindet das Fenster nach Pipeline-Ende sofort, kurze Hinweise wie "Pipeline beendet" oder die `FEHLER: prodsvcreport.svc.ch:1433 nicht erreichbar`-Meldung sind nur noch flüchtig sichtbar. Für die volle Diagnose bleibt `logs/newsanalysis.log` die Quelle der Wahrheit.
- **Rollback**: Falls Doppelklick-Sichtbarkeit doch nötig wird, kann das `pause >nul` am Ende wieder eingefügt werden — dann aber zwingend `MultipleInstances=Parallel` im Scheduler setzen oder den Task-Trigger anpassen, sonst tritt das Blocking-Problem erneut auf.
