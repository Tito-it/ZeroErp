## 📘 Documentazione Concettuale – Tabella `dbops.idempotency_keys`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[dbops.audit_log](/dbzero/dbops/tabelle/audit_log)
> [dbops.error_log](/dbzero/dbops/tabelle/error_log)

La tabella **`dbops.idempotency_keys`** è una **tabella tecnica** che associa l’**Idempotency-Key** inviata dal client alla **transazione DB (`tx_id`)** e alla **risposta serializzata**, garantendo **idempotenza forte** lato write.

---
### 🎯 Scopo Principale
(latest review 06-02-26)
* Prevenire doppie esecuzioni in caso di retry o chiamate duplicate.
* Restituire **la stessa risposta** quando arriva la stessa `idempotency_key`.
* Collegare operazioni applicative alla **tracciabilità transazionale** tramite `tx_id`.

---

### Significato dei Campi Chiave

* **`idempotency_key`**: chiave univoca inviata dal client (PK).
* **`request_id`**: correlation id applicativo (se disponibile).
* **`tx_id`**: UUID della transazione DB associata alla write.
* **`status`**: stato dell’elaborazione (`in_progress`, `completed`, `failed`).
* **`response_payload`**: risposta serializzata (JSONB) per replay idempotente.
* **`cleanup_at`**: timestamp opzionale per la pulizia programmata (non scadenza funzionale).

---

### Regole Principali

* **Univocità**: una `idempotency_key` identifica una sola operazione.
* **Stato**: `status` ammesso solo tra `in_progress|completed|failed`.
* **Coerenza**: quando `status = 'completed'`, `tx_id` deve essere valorizzato.

---

### Flusso Operativo

1. **Nuova richiesta** → inserisci record `in_progress`.
2. **Esecuzione completata** → aggiorni `completed` + `tx_id` + `response_payload`.
3. **Richiesta duplicata** → restituisci `response_payload` salvato.

---

### 🧹 Pulizia programmata (`cleanup_at`)

Il campo **`cleanup_at`** è pensato per **job periodici di cleanup** dei record idempotency.  
Non rappresenta una scadenza funzionale dell’operazione, ma solo la data consigliata per la rimozione.
