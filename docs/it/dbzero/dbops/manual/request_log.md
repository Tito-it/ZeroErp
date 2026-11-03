## 📘 Documentazione Concettuale – Tabella `dbops.request_log`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.sessioni_utente](/dbzero/dbops/tabelle/sessioni_utente) — la sessione dell'utente, legata dal `request_id`
> * [dbops.idempotency_keys](/dbzero/dbops/tabelle/idempotency_keys) — la chiave di idempotenza della stessa richiesta
> * [dbops.error_log](/dbzero/dbops/tabelle/error_log) — gli errori registrati, che scadono insieme alle chiamate
> * [dbops.ai_query_log](/dbzero/dbops/tabelle/ai_query_log) — le interazioni con l'assistente, legate dal `request_id`
>
> Approfondimento funzioni:
>
> * [dbops.trgfn_cleanup_at_alla_nascita](/dbzero/dbops/funzioni/trgfn_cleanup_at_alla_nascita) — scrive la scadenza all'inserimento
>
> Guide:
>
> * [Audit e tracciabilità](/guide/audit-e-tracciabilita) — i registri del sistema e come scadono
> * [Messaggi di errore e generazione log](/guide/Messaggi-di-Errore-e-Generazione-Log) — quale registro risponde a quale domanda

---

### 🎯 Scopo Principale

Il registro delle **chiamate HTTP alle API**: per ogni richiesta `/api/*` dice chi ha chiamato
quale percorso, con quale metodo, con quale esito e in quanto tempo. Risponde alla domanda «chi ha
chiamato cosa, via HTTP, e com'è andata?».

---

### Lo scrive il backend, a risposta pronta

La riga la scrive un middleware del backend, con un INSERT diretto, **dopo** che la risposta è
pronta: una per richiesta. Non si aggiorna: la tabella non ha le colonne di aggiornamento, e non ha
uno storico.

* I percorsi tecnici (salute, documentazione, schema, file statici) non si registrano: l'elenco sta
  in un building block del backend, non è configurabile.
* La registrazione si spegne da un'impostazione del backend; di default è accesa.
* Una scrittura che fallisce finisce nel log del backend e non ferma la risposta.
* ⛔ Il corpo della richiesta e della risposta non si registra, né per volume né per riservatezza.

⚠️ Poiché la riga nasce a risposta pronta, una richiesta che non arriva alla risposta (un processo
che muore, un timeout del gateway) **non lascia nessuna riga**. `status_code` e `duration_ms`
ammettono il vuoto, ma chi scrive oggi li valorizza sempre.

---

### Che cosa dice una riga

* `auth_user_id` e `username` sono l'utente riconosciuto, vuoti per una richiesta anonima;
  `username` è ricopiato per leggere senza join.
* `emittente_attivo_id` è l'emittente con cui l'utente lavorava: lo stesso che le policy RLS
  hanno usato in quella richiesta, preso dalla sessione e non dal token.
* `request_id` è l'identificativo che il middleware del contesto assegna alla richiesta: il filo
  verso `dbops.sessioni_utente`, `dbops.ai_query_log` e il log del backend.
* `method` sta nel vocabolario chiuso dal vincolo `chk_request_log_method` (`GET`, `POST`, `PUT`,
  `PATCH`, `DELETE`, `OPTIONS`, `HEAD`).
* `path` e `query_string` sono il percorso e i parametri della richiesta, troncati dal backend.
* `error_code` è il codice di errore dell'applicazione, preso dal corpo di una risposta di errore
  quando c'è.
* `idempotency_key` lega la richiesta alla sua chiave in `dbops.idempotency_keys`.
* `ip_address` e `user_agent` sono l'origine della richiesta.

⛔ Non c'è `tx_id`: la riga si scrive quando la transazione di lavoro è già chiusa, e un id coniato
a quel punto legherebbe la riga solo a se stessa. Per legare una chiamata ai suoi errori si usa il
`request_id` e l'orario.

---

### Scade dopo 90 giorni

Una riga resta **90 giorni**. La scadenza la scrive all'inserimento il trigger
`dbops.trgfn_cleanup_at_alla_nascita`, secondo la regola di scadenza della tabella, e il job di
pulizia cancella le righe scadute. `dbops.error_log` ha lo stesso termine: la chiamata e l'errore
che ne è uscito scadono insieme.

---

### Test

* `db/pgtap/dbops/test-registri-dbops-scadenza-v1.sql` — il registro è nello scope delle
  automazioni, con la sua regola e il trigger di scadenza alla nascita.

---

### Note di migrazione

* 2026-03-05 — nasce con il piano di audit delle sessioni e delle richieste
  (`Audit-logging-sessionii-request-token`).
* 2026-08-04 — entra `emittente_attivo_id`.
* 2026-08-24 — esce `tx_id`, che nessuno valorizzava e non si poteva valorizzare da chi scrive la
  riga.
* 2026-10-23 — entra nello scope delle automazioni: da quel giorno la regola di scadenza agisce.

---

{% include-markdown "signature-core.md" %}
