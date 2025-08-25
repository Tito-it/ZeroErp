@echo off
REM =========================================
REM  liquibase-mirror-upd.bat  (solo update)
REM  Usa --contexts="!test" di default
REM  Variabili opzionali (NON iniziare con LIQUIBASE_):
REM    LB_EXE       (path a liquibase.bat)
REM    LB_CONTEXTS  (default: !test)
REM =========================================

setlocal EnableExtensions DisableDelayedExpansion

set "HERE=%~dp0"
set "PROPS=%HERE%liquibase-mirror.properties"

REM Path CLI Liquibase (se non definito, prova alcuni default)
if not defined LB_EXE (
  if exist "C:\liquibase\liquibase-4.33.0\liquibase.bat" set "LB_EXE=C:\liquibase\liquibase-4.33.0\liquibase.bat"
)
if not defined LB_EXE (
  if exist "C:\Program Files\Liquibase\liquibase.bat" set "LB_EXE=C:\Program Files\Liquibase\liquibase.bat"
)
if not defined LB_EXE set "LB_EXE=liquibase"

if not defined LB_CONTEXTS set "LB_CONTEXTS=!test"

if not exist "%PROPS%" (
  echo [ERRORE] File non trovato: "%PROPS%"
  exit /b 1
)

echo [INFO] Liquibase exe: "%LB_EXE%"
echo [INFO] Properties:    "%PROPS%"
echo [INFO] Contexts:      %LB_CONTEXTS%
echo [INFO] Eseguo update...

call "%LB_EXE%" --defaults-file="%PROPS%" update --contexts="%LB_CONTEXTS%"
set "RC=%ERRORLEVEL%"

if %RC% NEQ 0 (
  echo [ERRORE] Liquibase ha restituito codice %RC%.
  exit /b %RC%
)

echo [OK] Update completato.
exit /b 0
