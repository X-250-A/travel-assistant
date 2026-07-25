@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
.venv\Scripts\python -X utf8 -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
