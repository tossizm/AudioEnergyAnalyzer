@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo [1/2] Removing unused PyInstaller _MEI folders...
for /d %%D in ("%TEMP%\_MEI*") do (
    rmdir /s /q "%%~fD" >nul 2>&1
    if exist "%%~fD" (
        echo Skipped in-use _MEI folder: %%~nxD
    ) else (
        echo Removed _MEI folder: %%~nxD
    )
)

echo.
echo [2/2] Removing project folders other than dist, config, ffmpeg...
for /d %%D in ("%CD%\*") do (
    if /I not "%%~nxD"=="dist" if /I not "%%~nxD"=="config" if /I not "%%~nxD"=="ffmpeg" (
        echo Removing: %%~nxD
        rmdir /s /q "%%~fD"
    )
)

REM Keep only the runtime resources under dist as well.
if exist "%CD%\dist" (
    for /d %%D in ("%CD%\dist\*") do (
        if /I not "%%~nxD"=="config" if /I not "%%~nxD"=="ffmpeg" (
            echo Removing dist subfolder: %%~nxD
            rmdir /s /q "%%~fD"
        )
    )
)

echo.
echo Cleanup complete. Preserved folders: dist, config, ffmpeg.
pause
endlocal
