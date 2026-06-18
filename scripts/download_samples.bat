@echo off
echo Smart EDA -- Downloading sample datasets...
echo.

cd /d d:\Developer\Auto-Data-Profiling-Smart-EDA-Report-Tool

REM Try venv python first
if exist ".venv\Scripts\python.exe" (
    echo Found .venv Python
    .venv\Scripts\python.exe scripts\download_samples.py
    goto done
)

REM Fallback: system python
python scripts\download_samples.py
if %errorlevel% == 0 goto done

REM Try py launcher
py scripts\download_samples.py

:done
echo.
echo Done! Check examples\ folder.
pause
