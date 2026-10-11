@echo off
if not exist "D:\PythonEnvs\ICBCRadar\Scripts\python.exe" (
  echo Existing ICBC virtual environment was not found at D:\PythonEnvs\ICBCRadar.
  pause
  exit /b 1
)
cd /d "%~dp0"
"D:\PythonEnvs\ICBCRadar\Scripts\python.exe" -m streamlit run app.py
pause
