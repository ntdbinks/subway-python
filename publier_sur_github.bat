@echo off
chcp 65001 >nul
title Publication sur GitHub
cd /d "%~dp0"
set "REPO=subway-python"
set "DESC=Runner 3D en perspective codé en Python avec Pygame : trains, bonus, génération procédurale, tests."
set "TAG=v2.0.0"

where git >nul 2>nul || goto sans_git
where gh >nul 2>nul || goto sans_gh
gh auth status >nul 2>nul || gh auth login --web --git-protocol https || goto erreur
for /f "delims=" %%i in ('gh api user --jq .login') do set "GHLOGIN=%%i"
for /f "delims=" %%i in ('gh api user --jq .id') do set "GHID=%%i"
echo Compte GitHub : %GHLOGIN%

if not exist ".git" git init -b main >nul
git config user.name >nul 2>nul || git config user.name "Nithard Mele"
git config user.email >nul 2>nul || git config user.email "%GHID%+%GHLOGIN%@users.noreply.github.com"
git add -A
git diff --cached --quiet || git commit -q -m "Subway Python v2 : rendu 3D en perspective, bonus, tests et build Windows" || goto erreur

gh repo view %GHLOGIN%/%REPO% >nul 2>nul && goto depot_existant
gh repo create %REPO% --public --source . --remote origin --description "%DESC%" --push || goto erreur
goto version

:depot_existant
git remote get-url origin >nul 2>nul || git remote add origin https://github.com/%GHLOGIN%/%REPO%.git
git push -u origin main || goto erreur

:version
rem le tag déclenche la construction de l'exécutable Windows sur GitHub Actions
git rev-parse %TAG% >nul 2>nul || git tag -a %TAG% -m "Version %TAG%"
git push origin %TAG% >nul 2>nul
echo.
echo Dépôt publié : https://github.com/%GHLOGIN%/%REPO%
echo L'exécutable Windows apparaîtra dans l'onglet « Releases » d'ici 5 à 10 minutes.
start "" https://github.com/%GHLOGIN%/%REPO%/actions
pause
exit /b 0

:sans_git
echo Git est nécessaire : https://git-scm.com/download/win
start "" https://git-scm.com/download/win
pause
exit /b 1

:sans_gh
echo GitHub CLI est nécessaire pour créer le dépôt.
choice /m "L'installer maintenant avec winget"
if errorlevel 2 exit /b 1
winget install --id GitHub.cli -e --accept-source-agreements --accept-package-agreements
echo Ferme cette fenêtre puis relance publier_sur_github.bat.
pause
exit /b 1

:erreur
echo.
echo La publication a échoué. Copie le message ci-dessus pour le diagnostic.
pause
exit /b 1
