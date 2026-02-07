# API throttling (Core Django)

## Scopo
Limitare burst di chiamate sugli endpoint search per proteggere backend e DB.

## Contesto
Implementazione in `apps/core/api/throttling.py` con classe `SearchBurstRateThrottle`.

## Input
- Request API
- View DRF con attributo `is_search_endpoint = True`

## Output
- Applicazione rate limit scope `search_burst`.
- Nessun throttling automatico sulle view che non marcano `is_search_endpoint`.

## Regole
- Attivazione selettiva: il throttle opera solo su endpoint search dichiarati.
- Configurazione rate da settings:
  - env `DJANGO_API_SEARCH_THROTTLE_RATE`
  - default `30/min`.
- In superamento limite, DRF risponde con `429`.

## Dipendenze DB
- Nessuna diretta.

## Note di migrazione
- Per nuove API search, impostare sempre `is_search_endpoint = True`.
- Per endpoint write, valutare throttling dedicato separato da quello search.
