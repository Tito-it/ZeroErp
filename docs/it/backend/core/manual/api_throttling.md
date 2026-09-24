# API throttling (Core Django)

## Scopo
Limitare burst di chiamate sugli endpoint search per proteggere backend e DB, e i
tentativi ripetuti sugli endpoint anonimi di login e reset password.

## Contesto
Implementazione in `apps/core/api/throttling.py`:

| Classe | Scope | Rate | Chiave | Dove si applica |
|---|---|---|---|---|
| `SearchBurstRateThrottle` | `search_burst` | da settings (vedi sotto) | IP | default DRF (`DEFAULT_THROTTLE_CLASSES`), attivo solo sulle view con `is_search_endpoint = True` |
| `LoginRateThrottle` | `login` | `5/5m` (fisso nella classe) | IP | viste di login (`auth_views.py`) |
| `PasswordResetRateThrottle` | `password_reset` | `3/15m` (fisso nella classe) | IP | reset password (`password_reset_views.py`), attivazione (`attivazione_view.py`), portale e shop |

`LoginRateThrottle` e `PasswordResetRateThrottle` derivano da `AnonRateThrottle`, con un
parsing del rate che accetta anche periodi in minuti/ore (`5m`, `15m`, `1h`). Una view che
dichiara `throttle_classes` sostituisce il default.

Il resto di questo documento riguarda `SearchBurstRateThrottle`.

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
