## 📘 Documentazione Concettuale – Tabella `vendite.event_log`

### 🎯 Scopo Principale

`vendite.event_log` centralizza in un unico stream temporale gli eventi tecnici/funzionali
dei domini vendite (pipeline, commesse, SDI, fatture), con modello **append-only**.

---

### ✅ Regole principali

* una riga per evento (nessun aggiornamento stato in-place);
* severita` standard: `INFO | WARN | ERROR`;
* correlazione opzionale cross-servizio tramite `correlation_id`;
* audit evento tramite `actor`, `source` e campi standard `data_insert/user_insert/data_update/user_update`;
* payload libero in `jsonb` per dettagli dominio.

---

### 🧱 Significato colonne

* `id`: identificativo tecnico progressivo dell'evento.
* `event_time`: data/ora evento usata per ordinare la timeline.
* `domain`: area funzionale (`PIPELINE`, `COMMESSE`, `SDI`, `FATTURE`).
* `entity_type`: tipo record tracciato (`LOTTO`, `FATTURA`, `COMMESSA`, `TASK_RUN`).
* `entity_id`: ID del record reale nel dominio indicato da `entity_type`.
* `event_code`: codice evento canonico (`STEP_STARTED`, `STEP_COMPLETED`, `PUSH_STARTED`, ...).
* `severity`: livello evento (`INFO`, `WARN`, `ERROR`).
* `correlation_id`: UUID di correlazione cross-servizio/job.
* `actor`: attore tecnico (`system`, `service:django`, `db:fn_xxx`).
* `source`: canale tecnico di emissione (`django`, `sql`, `api`).
* `payload`: dettaglio JSONB specifico del contesto evento.
* `data_insert`, `user_insert`, `data_update`, `user_update`: audit standard tabella.

---

### 🔒 Immutabilita`

La tabella e` protetta da trigger append-only:

* `UPDATE` non consentito;
* `DELETE` non consentito.

---

### 📎 Uso operativo

Le tabelle dominio specifiche (`commesse_push_log`, `fatturazione_lotti_task_runs`, `fatture_log`)
restano per query specialistiche; `event_log` abilita la timeline unificata per audit/debug.

---

### 🧪 Esempi

Timeline di un lotto:

```sql
SELECT event_time, event_code, severity, actor, source, payload
FROM vendite.event_log
WHERE entity_type = 'LOTTO'
  AND entity_id = 123
ORDER BY event_time;
```

Eventi di una finestra temporale:

```sql
SELECT event_time, domain, entity_type, entity_id, event_code, severity
FROM vendite.event_log
WHERE event_time >= now() - interval '1 hour'
ORDER BY event_time;
```

Ricostruzione per correlation id:

```sql
SELECT event_time, domain, entity_type, entity_id, event_code, payload
FROM vendite.event_log
WHERE correlation_id = '11111111-1111-1111-1111-111111111111'::uuid
ORDER BY event_time;
```

---

{% include-markdown "signature-core.md" %}
