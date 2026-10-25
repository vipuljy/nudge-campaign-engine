@echo off
REM One command to start the Nudge app: double-click this file, or type run_app in this folder.
cd /d "%~dp0"
.venv\Scripts\python.exe -m streamlit run app.py
