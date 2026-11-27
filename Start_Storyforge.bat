@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo STORYFORGE: Python-Umgebung wird eingerichtet ...
  py -m venv .venv || goto :error
)
".venv\Scripts\python.exe" -c "import fastapi,uvicorn,storyforge" >nul 2>nul
if errorlevel 1 (
  echo STORYFORGE: Abhaengigkeiten werden installiert ...
  ".venv\Scripts\python.exe" -m pip install -e . || goto :error
)
".venv\Scripts\python.exe" -m storyforge.web
if errorlevel 1 goto :error
exit /b 0
:error
echo Start fehlgeschlagen. Bitte Python 3.10+ und Internetzugang fuer die Ersteinrichtung pruefen.
pause
exit /b 1
