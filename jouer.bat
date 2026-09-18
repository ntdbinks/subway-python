@echo off
chcp 65001 >nul
title Subway Python
cd /d "%~dp0"

rem Prépare l'environnement : relancé automatiquement si une installation précédente a échoué
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -c "import pygame" >nul 2>nul && goto pret
)
set "PY=python"
where py >nul 2>nul && set "PY=py -3"
%PY% -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>nul
if errorlevel 1 goto sans_python
echo Installation du jeu, environ 1 minute...
if not exist ".venv\Scripts\python.exe" %PY% -m venv .venv || goto erreur
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto erreur
".venv\Scripts\python.exe" -c "import pygame" || goto erreur
:pret

start "" ".venv\Scripts\pythonw.exe" main.py
exit /b 0

:sans_python
echo Python 3.10 ou plus récent est introuvable.
echo Installe-le depuis https://www.python.org/downloads/ en cochant « Add python.exe to PATH ».
start "" https://www.python.org/downloads/
pause
exit /b 1

:erreur
echo.
echo L'installation a échoué. Copie le message ci-dessus pour le diagnostic.
pause
exit /b 1
