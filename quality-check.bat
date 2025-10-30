@echo off
REM Run all code quality checks

echo ======================================
echo Running Code Quality Checks
echo ======================================
echo.

echo 1. Checking code formatting...
echo ------------------------------
uv run black --check --diff .

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Quality checks failed!
    exit /b 1
)

echo.
echo ======================================
echo All quality checks passed!
echo ======================================
