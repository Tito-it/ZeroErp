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

**Quale «IP».** Tutte e tre le classi prendono la chiave da `get_client_ip`
(`apps/core/services/request_context.py`), non dalla lettura propria di DRF: il valore
di `X-Forwarded-For` di cui fidarsi lo decide il setting obbligatorio
`TRUSTED_PROXY_COUNT` (env `DJANGO_TRUSTED_PROXY_COUNT`, 1 con Nginx), contando **da
destra**. I valori a sinistra li scrive il client, e cambiarli non dà un contatore nuovo.
Le richieste di cui l'IP non si ricava condividono un contatore solo (`ip-sconosciuto`).
⛔ Un throttle nuovo deriva da queste classi: `get_ident` di DRF, con `NUM_PROXIES` non
impostato, userebbe l'header intero.

⚠️ **`LoginRateThrottle` non e' il freno dei tentativi falliti.** Conta le
**richieste** per IP, qualunque credenziale provino: ferma chi inonda l'endpoint.
Il freno per credenziale + provenienza (DB, `config.credenziali`) conta le
**password sbagliate** su una credenziale: ferma chi la prova. Due regole, anche
se oggi i numeri (5 e 5) coincidono — vedi
[guida multi-face §3.1-bis](../../../guide/architettura-multi-face-auth.md).

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
