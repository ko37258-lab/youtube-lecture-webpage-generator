@echo off
title Lecture Content Generator

echo.
echo  ==========================================
echo    YouTube Lecture Content Generator
echo  ==========================================
echo.
echo   Your web browser will open shortly.
echo   First launch may take about 20 seconds.
echo.
echo   To quit: just close this black window.
echo.
echo  ------------------------------------------
echo.

cd /d "%~dp0"

"C:\Users\chul7\AppData\Local\Programs\Python\Python311\Scripts\streamlit.exe" run app.py

echo.
pause