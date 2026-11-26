@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Creating local Python environment...
  py -3 -m venv .venv
  if errorlevel 1 (
    echo Python 3 was not found. Install Python 3.11 or newer and retry.
    pause
    exit /b 1
  )
)
if not exist .env (
  copy .env.example .env >nul
  echo Created worker\.env. Edit it and set RF983_WORKER_TOKEN before continuing.
  notepad .env
  pause
  exit /b 0
)
for /f "usebackq tokens=1,* delims==" %%A in (".env") do if not "%%A"=="" if not "%%A:~0,1"=="#" set "%%A=%%B"
.venv\Scripts\python.exe worker.py
pause
