@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" python -m venv .venv
call .venv\Scripts\activate
if errorlevel 1 (
    echo FAILED: Could not activate the virtual environment.
    if not defined CI pause
    exit /b 1
)

python -m pip install --upgrade pip
if errorlevel 1 (
    echo FAILED: Could not upgrade pip.
    if not defined CI pause
    exit /b 1
)
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo FAILED: Could not install requirements.
    if not defined CI pause
    exit /b 1
)

python -m pytest -q
if errorlevel 1 (
    echo TESTS FAILED.
    if not defined CI pause
    exit /b 1
)

if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
pyinstaller --noconfirm --clean --onefile --windowed ^
  --name AudioEnergyAnalyzer ^
  --paths "." ^
  --collect-all av ^
  app\main.py

if errorlevel 1 (
    echo BUILD FAILED.
    if not defined CI pause
    exit /b 1
)

if not exist "dist\AudioEnergyAnalyzer.exe" (
    echo BUILD FAILED: dist\AudioEnergyAnalyzer.exe was not created.
    if not defined CI pause
    exit /b 1
)

REM External runtime resources are deliberately copied beside the EXE.
if not exist "dist\config" mkdir "dist\config"
xcopy /E /I /Y "config\*" "dist\config\"
if errorlevel 1 (
    echo FAILED: Could not copy config files.
    if not defined CI pause
    exit /b 1
)
if exist "ffmpeg" (
    if not exist "dist\ffmpeg" mkdir "dist\ffmpeg"
    xcopy /E /I /Y "ffmpeg\*" "dist\ffmpeg\"
    if errorlevel 1 (
        echo FAILED: Could not copy ffmpeg files.
        if not defined CI pause
        exit /b 1
    )
)

if not exist "dist\config\Reference_Average_Default.json" (
    echo WARNING: default reference JSON was not found in dist\config.
)

echo BUILD COMPLETE:
echo %CD%\dist\AudioEnergyAnalyzer.exe
echo External config: %CD%\dist\config
if exist "dist\ffmpeg" echo External ffmpeg: %CD%\dist\ffmpeg
echo.
echo Cleaning unused PyInstaller _MEI temporary folders...
for /d %%D in ("%TEMP%\_MEI*") do (
    rmdir /s /q "%%~fD" >nul 2>&1
    if exist "%%~fD" (
        echo Skipped in-use _MEI folder: %%~nxD
    ) else (
        echo Removed _MEI folder: %%~nxD
    )
)

echo.
echo To remove development folders after confirming the EXE works,
echo run cleanup_after_build.bat separately.
if not defined CI pause
endlocal
