# API routing core (Core Django)

## Scopo
Documentare il routing core tra path legacy e path versionato v1.

## Contesto
Routing locale:
- `apps/core/api/urls.py`
- `apps/core/api/urls_v1.py`

Include a livello progetto:
- `zeroerp_backend/urls.py`

## Input
- Path base `/api/core/...` (legacy/compatibilita`)
- Path base `/api/v1/core/...` (canonico)

## Output
- Endpoint diagnostico:
  - `/api/core/diagnostics/error-envelope/`
  - `/api/v1/core/diagnostics/error-envelope/`

## Regole
- La versione canonica da usare nelle integrazioni nuove e` `/api/v1/*`.
- Le route legacy sono controllate dalle policy di compatibilita` del progetto.
- Le route v1 devono essere protette con JWT dove previsto.

## Dipendenze DB
- Nessuna diretta.

## Note di migrazione
- Progressivamente deprecare uso diretto di `/api/core/*` a favore di `/api/v1/core/*`.
