@echo off
REM Quick start script for generating paper figures
REM Usage: double-click or run from command line

echo ======================================================================
echo Paper Figures Generator for hw-1 Project
echo ======================================================================
echo.

cd /d "%~dp0"

REM Activate virtual environment
if exist "..\\.venv-mujoco\\Scripts\\activate.bat" (
    echo Activating virtual environment...
    call "..\\.venv-mujoco\\Scripts\\activate.bat"
) else (
    echo Warning: Virtual environment not found, using system Python
)

echo.
echo Choose an option:
echo   1. Generate all figures (default)
echo   2. Generate specific figures
echo   3. Generate high-res PNG only (600 DPI)
echo   4. Generate PDF only (for LaTeX)
echo   5. Exit
echo.

set /p choice="Enter choice (1-5): "

if "%choice%"=="" set choice=1
if "%choice%"=="5" exit /b

if "%choice%"=="1" (
    echo Generating all figures in all formats...
    python generate_all.py
)

if "%choice%"=="2" (
    set /p figures="Enter figure numbers (comma-separated, e.g., 1,3,5): "
    python generate_all.py --figures %figures%
)

if "%choice%"=="3" (
    echo Generating high-resolution PNG (600 DPI)...
    python generate_all.py --format png --dpi 600
)

if "%choice%"=="4" (
    echo Generating PDF only (for LaTeX)...
    python generate_all.py --format pdf
)

echo.
echo ======================================================================
echo Generation complete! Check output folder for results.
echo ======================================================================
echo.
echo Output directory: output\
echo   - PDF files: output\pdf\
echo   - PNG files: output\png\
echo   - SVG files: output\svg\
echo   - LaTeX index: output\figures_index.tex
echo.
pause
