# Endpoint sessioni attive utente — /api/v1/core/me/sessioni/

## Scopo

Permette all'utente autenticato di visualizzare le proprie sessioni attive
(esclusa quella corrente) e di revocare sessioni sospette.

## Contesto

Il frontend chiama `GET /me/sessioni/` per popolare il pannello sessioni attive
nella home. Se la lista e' vuota, il pannello non viene mostrato. L'utente puo'
revocare una sessione specifica tramite `POST /me/sessioni/<jti>/revoca/`.

⚠️ **`jti` qui vuol dire sessione, non token.** La colonna `dbops.sessioni_utente.jti`,
il campo `jti` della risposta e il parametro URL `<jti>` portano il **`sid`**: il claim
di sessione messo nel refresh token al login e copiato su access token e refresh
ruotati. Una sessione e' quindi l'insieme di tutti i token JWT con lo stesso `sid`.

Una sessione e' considerata "attiva" se il suo ultimo evento nella tabella
`dbops.sessioni_utente` e' LOGIN o REFRESH e il timestamp e' entro 1 giorno
(TTL del refresh token). La query usa una CTE con `ROW_NUMBER()` per determinare
l'ultimo evento per ogni `sid`.

---

## GET /api/v1/core/me/sessioni/ — Lista sessioni attive

### Input

- **Autenticazione**: JWT Bearer token (header `Authorization: Bearer <access_token>`)
- **Parametri**: nessuno — usa `request.user.id` e il `sid` del token corrente

### Output

Envelope standard `{ "data": {...}, "meta": {...} }`.

| Campo | Tipo | Descrizione |
|---|---|---|
| `data.sessioni` | array | Lista sessioni attive (esclusa la corrente) |
| `data.count` | integer | Numero sessioni restituite |

Ogni elemento di `sessioni`:

| Campo | Tipo | Descrizione |
|---|---|---|
| `jti` | string | `sid` della sessione (non il JWT ID) |
| `ultimo_evento` | string | LOGIN o REFRESH |
| `ip_address` | string | Indirizzo IP del client |
| `user_agent` | string | User-Agent del browser/client |
| `data_inizio` | datetime | Timestamp del primo LOGIN |
| `data_ultimo_evento` | datetime | Timestamp dell'ultimo evento |

### Esempio risposta

```json
{
  "data": {
    "sessioni": [
      {
        "jti": "a1b2c3d4-...",
        "ultimo_evento": "REFRESH",
        "ip_address": "192.168.1.10",
        "user_agent": "Mozilla/5.0 ...",
        "data_inizio": "2026-03-09T08:00:00",
        "data_ultimo_evento": "2026-03-09T10:30:00"
      }
    ],
    "count": 1
  },
  "meta": { "request_id": "..." }
}
```

### Regole

- La sessione corrente (identificata dal claim `sid` del token di accesso) e' sempre esclusa dalla lista
- Vengono restituite solo sessioni con ultimo evento LOGIN o REFRESH e timestamp entro 1 giorno
- Se non ci sono altre sessioni attive, `sessioni` e' una lista vuota e `count` e' 0

---

## POST /api/v1/core/me/sessioni/<jti>/revoca/ — Revoca sessione

### Input

- **Autenticazione**: JWT Bearer token (header `Authorization: Bearer <access_token>`)
- **URL param**: `jti` (string) — `sid` della sessione da revocare
- **Body**: nessuno

### Output

- **204 No Content** — sessione revocata con successo
- Nessun body nella risposta

### Regole

- Non e' possibile revocare la sessione corrente — restituisce `E_SESSIONE_REVOCA_CORRENTE` (400)
- Il `sid` deve corrispondere ad almeno un `OutstandingToken` dell'utente corrente — altrimenti `E_SESSIONE_NOT_FOUND` (404)
- La revoca esegue: blacklist di **tutti** i token con quel `sid` (`BlacklistedToken.objects.bulk_create(..., ignore_conflicts=True)`, saltando quelli gia' bloccati) + INSERT evento REVOCA in `dbops.sessioni_utente`
- Idempotente: se i token della sessione esistono ma sono gia' tutti bloccati, la risposta resta **204** (non 404)
- L'operazione e' sicura: un utente puo' revocare solo le proprie sessioni (filtro `user_id`)

---

## POST /api/v1/core/me/sessioni/revoca-tutte/ — Revoca tutte le altre

Revoca **tutte** le sessioni dell'utente corrente **tranne quella da cui arriva
la richiesta**. Input: nessun body.

I due effetti hanno perimetri diversi:

- **Blacklist**: tutti i token dell'utente con `sid` valorizzato e diverso da quello corrente.
- **Audit**: un evento `REVOCA` per ogni sessione **attiva** (la stessa lettura di
  `GET /me/sessioni/`) diversa dalla corrente — non per ogni `sid` mai emesso.

Output **200**:

```json
{ "data": { "revoked": 2 }, "meta": { "request_id": "..." } }
```

`revoked` = numero di sessioni attive revocate (quelle per cui e' stato scritto l'evento).

⚠️ L'esclusione della sessione corrente non e' una comodita': se revocasse anche
la propria, l'operatore che clicca «esci da tutti i dispositivi» verrebbe
buttato fuori dal dispositivo che ha in mano, senza sapere se l'operazione e'
riuscita. Il caso d'uso — «ho perso il telefono» — vuole esattamente il
contrario.

## Dipendenze DB

| Funzione/Tabella | Schema | Ruolo |
|---|---|---|
| `sessioni_utente` | `dbops` | Query CTE sessioni attive + INSERT evento REVOCA |
| `token_blacklist_outstandingtoken` | Django | Lookup token per JTI + user_id |
| `token_blacklist_blacklistedtoken` | Django | Blacklist token revocato |

## File backend

| File | Ruolo |
|---|---|
| `apps/core/api/sessioni_view.py` | `SessioniAttiveListView` (GET) + `SessioneRevocaView` (POST) + `SessioniRevocaTutteView` (POST) |
| `apps/core/db/session_audit_repository.py` | `list_sessioni_attive()` — CTE query + `log_session_event()` |
| `apps/core/services/session_audit_service.py` | `record_revoca()` — delega INSERT al repository |
| `apps/core/api/urls_v1.py` | Rotte `me/sessioni/`, `me/sessioni/revoca-tutte/` e `me/sessioni/<str:jti>/revoca/` |
| `apps/core/services/error_policies_generated.py` | Classi `E_SESSIONE_NOT_FOUND`, `E_SESSIONE_REVOCA_CORRENTE` |
| `apps/core/tests/api/test_sessioni_view.py` | Test: lista, revoca singola, revoca-tutte, logout, repository |

## Errori

| Codice | HTTP | Quando |
|---|---|---|
| `E_SESSIONE_REVOCA_CORRENTE` | 400 | Tentativo di revocare la sessione corrente |
| `E_SESSIONE_NOT_FOUND` | 404 | Nessun token dell'utente con quel `sid` |

## Note di migrazione

- La tabella `dbops.sessioni_utente` deve essere presente (changeset Liquibase `20260305-01`)
- Le tabelle SimpleJWT blacklist devono essere migrate (`token_blacklist` in `INSTALLED_APPS`)
