## Documentazione Concettuale -- Tabella `dbops.request_log`

> **Vedi anche**
>
**Piano di riferimento:**
>
[Audit Sessioni, Request Logging e Sicurezza Token](/dev/work-done/Audit-logging-sessionii-request-token)
>
**Tabelle correlate:**
>
[dbops.sessioni_utente](/dbzero/dbops/manual/sessioni_utente) -- correlazione via `request_id`
> [dbops.idempotency_keys](/dbzero/dbops/manual/idempotency_keys) -- correlazione via `idempotency_key`
> [dbops.audit_log](/dbzero/dbops/manual/audit_log) -- pattern retention `cleanup_at`
>
### 🎯 Scopo Principale
(latest review 05-03-2026)

`dbops.request_log` registra **ogni request API** (`/api/*`) in transito nel sistema:
utente, endpoint, metodo HTTP, status code, durata e metadati di correlazione.

Risponde alle domande:

* Quale utente ha chiamato quale endpoint, quando e con quale esito?
* Quanto tempo ha impiegato una specifica request?
* Ci sono pattern di errore ricorrenti su determinati path?
* Una request con idempotency key e` stata ripetuta?

---

### Campi chiave

| Colonna | Ruolo |
|---------|-------|
| `auth_user_id` | Riferimento utente Django (NULL se request anonima). |
| `username` | Username JWT denormalizzato per query rapide senza join. |
| `request_id` | UUID dalla `RequestContextMiddleware` -- chiave di correlazione universale. |
| `method` | Metodo HTTP. Validato da CHECK: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS`, `HEAD`. |
| `path` | Path della request (es. `/api/v1/pratiche/`). |
| `query_string` | Parametri query (senza dati sensibili). |
| `status_code` | HTTP status code. **Nullable**: una transazione interrotta (crash, timeout) non ha response. |
| `duration_ms` | Durata in millisecondi. **Nullable**: stesso motivo di `status_code`. |
| `error_code` | Codice errore applicativo (es. `E_PRATICA_NOT_FOUND`), se presente nella response. |
| `idempotency_key` | Chiave idempotenza per correlazione con `dbops.idempotency_keys`. |
| `tx_id` | Transaction ID (pattern standard dbops, trigger `trgfn_tx_id_managed`). |
| `cleanup_at` | Timestamp retention per pulizia schedulata (es. 90 giorni). |

---

### Caratteristiche tecniche

* **Insert-only**: la tabella non prevede UPDATE. Non ha colonne `data_update` / `user_update`.
* **No storicizzazione**: essendo gia` un log, non necessita di snapshot temporali.
* **Volume alto**: una riga per ogni request `/api/*`. Valutare partizionamento per mese se il volume lo richiede.
* **Retention**: 90 giorni (regola CLEANUP_AT id=14). La scadenza la scrive all'INSERT il trigger `trg_request_log_m50_cleanup_at_ins` e il job settimanale cancella le righe scadute; la tabella è nello scope delle automazioni dal 2026-10-23 (prima la regola non agiva). Dettaglio nella guida [Audit e tracciabilità](/guide/audit-e-tracciabilita).
* **Grant**: automatici via CI grant dinamico su schema `dbops`.
* **Sicurezza**: il middleware NON logga body request/response (dati sensibili + volume). Solo header-level.

---

### Indici

| Nome | Colonne | Scopo |
|------|---------|-------|
| `ix_request_log_auth_user_id` | `auth_user_id` | Ricerca log per utente. |
| `ix_request_log_data_insert` | `data_insert DESC` | Ordinamento cronologico, query recenti. |
| `ix_request_log_path` | `path` | Ricerca/aggregazione per endpoint. |
| `ix_request_log_request_id` | `request_id` | Correlazione con `sessioni_utente` e tracing. |
| `ix_request_log_cleanup_at` | `cleanup_at` | Supporto job pulizia retention. |

---

### Ruolo operativo

1. Il middleware `RequestLogMiddleware` inserisce un record per ogni request `/api/*`.
2. I percorsi tecnici (health, docs, schema, static, media) non si registrano: elenco nel BB backend `apps/core/services/percorsi_tecnici.py`, non configurabile.
3. Il logging e` disattivabile via `DJANGO_REQUEST_LOG_ENABLED` (default: attivo).
4. Il job di pulizia schedulato elimina i record oltre la retention configurata.
5. L'API di consultazione (fase 2, solo ADMIN) espone i dati con filtri user/data/path/status.

---

### Segnali diagnostici

Un record con `status_code IS NULL AND duration_ms IS NULL` indica una **request
che non ha mai completato** (crash processo, OOM, timeout gateway). Questi record
sono spesso i piu` interessanti da investigare:

```sql
SELECT request_id, auth_user_id, method, path, data_insert
  FROM dbops.request_log
 WHERE status_code IS NULL
 ORDER BY data_insert DESC;
```

---

### Correlazione con sessioni_utente

Il campo `request_id` condiviso consente di correlare ogni request alla sessione
JWT che l'ha generata:

```sql
SELECT r.method, r.path, r.status_code, r.duration_ms, s.evento
  FROM dbops.request_log r
  LEFT JOIN dbops.sessioni_utente s USING (request_id)
 WHERE r.auth_user_id = :user_id
   AND r.data_insert >= :da_data;
```

---

> **In sintesi**: `request_log` fornisce visibilita` completa su chi chiama cosa nel sistema,
> colmando una lacuna critica per audit, diagnostica e monitoraggio delle API.

---

{% include-markdown "signature-core.md" %}
