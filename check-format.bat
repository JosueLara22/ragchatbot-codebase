@echo off
REM Check code formatting without making changes

echo Checking code formatting with black...
uv run black --check --diff .

if %ERRORLEVEL% EQU 0 (
    echo.
    echo All files are properly formatted!
    exit /b 0
) else (
    echo.
    echo Some files need formatting. Run format.bat to fix.
    exit /b 1
)
