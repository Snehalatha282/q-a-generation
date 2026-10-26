@echo off
title AI Academic Assistant
echo ============================================================
echo   AI Academic Assistant: Intelligent PDF Analysis
echo   and Scheme-Based Answer Generation
echo ============================================================
echo.
echo Starting Streamlit Web Application...
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
cd /d "%~dp0"
python -m streamlit run app.py
pause
