@echo off
rem Run Lightshow from source. First run creates a virtual env and installs dependencies.
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
    echo Setting up Python environment...
    py -3 -m venv .venv || goto :error
    .venv\Scripts\python.exe -m pip install --upgrade pip
    .venv\Scripts\python.exe -m pip install -r requirements.txt || goto :error
)
.venv\Scripts\python.exe main.py
exit /b

:error
echo.
echo Setup failed. Make sure Python 3 is installed from python.org.
pause
