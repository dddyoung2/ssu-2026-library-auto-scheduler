@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Python 3.10 virtual environment...
  py -3.10 -m venv .venv
  if errorlevel 1 goto :error
)

echo [2/3] Installing packages...
.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 goto :error
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo [3/3] Starting server...
start "" http://127.0.0.1:8000
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
goto :eof

:error
echo.
echo Installation or execution failed. Check the message above.
pause
exit /b 1
