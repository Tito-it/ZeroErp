@echo off
REM --- Carica internal.env in variabili d'ambiente CMD ---
for /f "usebackq tokens=1,* delims==" %%A in ("internal.env") do (
  set %%A=%%B
)

REM --- Verifica (opzionale) ---
echo DB_HOST = %DB_HOST%
echo DB_PORT = %DB_PORT%
echo DB_NAME = %DB_NAME%
echo POSTGRESQL_USER = %POSTGRESQL_USER%
echo POSTGRESQL_PWD = %POSTGRESQL_PWD%

REM --- Esegui Liquibase con URL e credenziali espanse ---
liquibase ^
  --url=jdbc:postgresql://%DB_HOST%:%DB_PORT%/%DB_NAME% ^
  --username=%POSTGRESQL_USER% ^
  --password=%POSTGRESQL_PWD% ^
  validate
