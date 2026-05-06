@echo off
cd /d %~dp0
if not exist backups mkdir backups
for /f "tokens=1-4 delims=/ " %%a in ("%date%") do set d=%%a-%%b-%%c
copy app\skola_royale.db backups\skola_royale_backup_%random%.db
echo Backup complete.
pause
