# update-venv.ps1
# Aggiorna tutti i pacchetti nella venv, esegue 'pip check' e,
# se non ci sono conflitti, scrive requirements.txt

# In alternativa usare questi comandi manualmente:

# python -m pip install --upgrade pip
# python -m pip list --outdated --format=json
# python -m pip install --upgrade <package_name>
# python -m pip check
# pip list --outdated --format=columns | ForEach-Object { if ($_ -match '^\S+') { pip install --upgrade $matches[0] } } -- aggiorna tutto
# python -m pip freeze > requirements.txt
#


$ErrorActionPreference = "Stop"

# 0) Check venv
if (-not $env:VIRTUAL_ENV) {
    Write-Warning "Non sembra attiva una virtualenv (VIRTUAL_ENV non impostata)."
    $resp = Read-Host "Vuoi continuare lo stesso? [y/N]"
    if ($resp -ne 'y') { exit 1 }
}

# 1) Aggiorna pip (sicuro)
python -m pip install --upgrade pip

# 2) Elenco pacchetti da aggiornare (formato JSON, più affidabile)
$outdatedJson = python -m pip list --outdated --format=json
$outdated = @()
if ($outdatedJson) {
    try {
        $outdated = $outdatedJson | ConvertFrom-Json
    } catch {
        Write-Warning "Impossibile leggere JSON da 'pip list'."
    }
}

if (-not $outdated -or $outdated.Count -eq 0) {
    Write-Host "Nessun pacchetto da aggiornare."
} else {
    foreach ($pkg in $outdated) {
        $name = $pkg.name
        Write-Host "⟹ Aggiorno $name ..."
        python -m pip install --upgrade $name
    }
}

# 3) Verifica dipendenze
Write-Host "`nEseguo 'pip check'..."
$checkOutput = & python -m pip check 2>&1
$exitCode = $LASTEXITCODE
Write-Host $checkOutput

# 4) Se ok, congela versions
if ($exitCode -eq 0) {
    Write-Host "`n✅ Dipendenze OK. Scrivo requirements.txt..."
    python -m pip freeze | Out-File -FilePath requirements.txt -Encoding ASCII
    Write-Host "Fatto: requirements.txt aggiornato."
    exit 0
} else {
    Write-Error "❌ Conflitti rilevati. requirements.txt NON aggiornato. Risolvi e riprova."
    exit $exitCode
}
