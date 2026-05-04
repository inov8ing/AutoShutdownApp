@echo off
cd /d "%~dp0"
echo Starting Auto Shutdown Widget...
start "" pythonw AutoShutdownApp.pyw
exit
