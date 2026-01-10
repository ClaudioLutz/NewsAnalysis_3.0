# Windows Task Scheduler Automation and Bug Fixes

## Summary

Added Windows Task Scheduler automation for daily pipeline execution. Fixed meta-analysis generation bug caused by incorrect PromptConfig access. Added pywin32 dependency for Outlook email integration.

## Context / Problem

1. **Manual daily execution**: The pipeline required manual execution each day via command line
2. **Email not sending**: The email service failed with "pywin32 not installed" error
3. **Meta-analysis failing**: Digest generation logged `'PromptConfig' object has no attribute 'get'` error

## What Changed

### run_daily.bat (NEW)
Created batch file for Task Scheduler to execute:
```batch
@echo off
cd /d "c:\Lokal_Code\NewsAnalysis_3.0"
call venv\Scripts\activate.bat
python -m newsanalysis.cli.main run
```

### src/newsanalysis/pipeline/generators/digest_generator.py
Fixed PromptConfig access - changed dictionary-style `.get()` calls to direct attribute access:
```python
# Before (broken)
system_prompt = self.prompt_config.get("system_prompt", "")
user_template = self.prompt_config.get("user_prompt_template", "")

# After (fixed)
system_prompt = self.prompt_config.system_prompt
user_template = self.prompt_config.user_prompt_template
```

### Dependencies
- Added `pywin32` to venv for Outlook COM integration

## Task Scheduler Setup

### Via PowerShell (run as Admin):
```powershell
$action = New-ScheduledTaskAction -Execute "c:\Lokal_Code\NewsAnalysis_3.0\run_daily.bat" -WorkingDirectory "c:\Lokal_Code\NewsAnalysis_3.0"
$trigger = New-ScheduledTaskTrigger -Daily -At 7:00AM
$settings = New-ScheduledTaskSettingsSet -WakeToRun
Register-ScheduledTask -TaskName "NewsAnalysis Daily Run" -Action $action -Trigger $trigger -Settings $settings -Description "Run news analysis pipeline daily"
```

### Prerequisites for Wake-to-Run:
1. Control Panel -> Power Options
2. Change plan settings -> Change advanced power settings
3. Sleep -> Allow wake timers -> Enable

### Via GUI:
1. Win + R -> `taskschd.msc`
2. Create Basic Task -> "NewsAnalysis Daily Run"
3. Trigger: Daily at preferred time
4. Action: Start Program -> `run_daily.bat`
5. Properties: "Run whether user is logged on or not"
6. Conditions: "Wake the computer to run this task"

## Results

| Issue | Status |
|-------|--------|
| Daily automation | Configured via Task Scheduler |
| Email sending | Fixed (pywin32 installed) |
| Meta-analysis generation | Fixed (attribute access) |

## How to Test

1. Run the pipeline manually:
   ```bash
   python -m newsanalysis.cli.main run --reset digest --skip-collection
   ```

2. Verify meta-analysis generates without errors in logs

3. Verify email sends successfully

4. Test Task Scheduler:
   ```powershell
   Start-ScheduledTask -TaskName "NewsAnalysis Daily Run"
   ```

## Risk / Rollback Notes

- **Risk**: Task Scheduler only works if laptop is on/sleeping (not shut down)
- **Risk**: Wake timers must be enabled in power settings
- **Rollback**: Delete scheduled task via `Unregister-ScheduledTask -TaskName "NewsAnalysis Daily Run"`
