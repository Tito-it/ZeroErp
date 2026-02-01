param(
  [string]$DbHost    = 'localhost',
  [int]   $DbPort    = 5432,
  [string]$DbName    = 'zeroerp',
  [string]$DbUser    = 'zeroerp',
  [string]$DbPass    = 'secret',
  [string]$Changelog = 'db/changelog/changelog-master.yaml',
  [string]$Liquibase = 'liquibase'
)

$ErrorActionPreference = 'Stop'

$base = "jdbc:postgresql://$DbHost:$DbPort/$DbName"
$optsNoDblink = '?options=-c%20myapp.log_with_dblink%3Doff'
$optsCi       = "$optsNoDblink%20-c%20myapp.env%3Dci"

Write-Host "==> Liquibase base update (no test contexts)…"
& $Liquibase `
  --url="$base$optsNoDblink" `
  --username="$DbUser" `
  --password="$DbPass" `
  --changeLogFile="$Changelog" `
  update --contexts="!test"

Write-Host "==> Liquibase CI apply (runner/automations)…"
& $Liquibase `
  --url="$base$optsCi" `
  --username="$DbUser" `
  --password="$DbPass" `
  --changeLogFile="$Changelog" `
  update --contexts="ci_apply"

Write-Host "==> Done."
