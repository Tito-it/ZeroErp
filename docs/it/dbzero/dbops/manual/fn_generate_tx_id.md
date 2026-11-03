## 📘 Documentazione Concettuale – Funzione `dbops.fn_generate_tx_id`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.transaction_ids](/dbzero/dbops/tabelle/transaction_ids) — il registro in cui scrive
> * [dbops.sec_functions_owner](/dbzero/dbops/tabelle/sec_functions_owner) — dove è dichiarato il suo proprietario
>
> Approfondimento funzioni:
>
> * [dbops.fn_get_or_create_session_tx_id](/dbzero/dbops/funzioni/fn_get_or_create_session_tx_id) — la chiama, su una connessione separata
>
> Guide:
>
> * [Transaction ID](/guide/tx_id_implementation_guide) — come nasce e come si propaga il `tx_id`

---

### 🎯 Scopo Principale

Genera un **transaction id nuovo**, un UUID v7, lo registra in `dbops.transaction_ids` con la
funzione che l'ha chiesto e il suo contesto, e lo restituisce.

È il solo punto in cui un `tx_id` nasce registrato: non legge la sessione e non pubblica niente.
Riusare l'id della transazione, o pubblicarlo, è il mestiere di
`dbops.fn_get_or_create_session_tx_id`, che la chiama.

---

### Si chiama dalla connessione di log

L'unico chiamante è `dbops.fn_get_or_create_session_tx_id`, che la esegue attraverso `dblink`
sulla connessione di log: così la riga del registro si conferma subito, fuori dalla transazione di
lavoro, e sopravvive al suo annullamento. Chiamata direttamente, nella transazione di chi chiama,
la registrazione seguirebbe quella transazione.

---

### ⚠️ Gira come `postgres`, con il percorso di ricerca fissato

È `SECURITY DEFINER`, e il proprietario è `postgres`, dichiarato nel registro dei proprietari delle
funzioni: chi la esegue (il ruolo del canale di log) non ha bisogno di scrivere nel registro dei
transaction id. Per questo il percorso di ricerca è fissato nella definizione, e un rifacimento che
lo dimentica lo azzera.

Modificarla chiede di passare dal registro dei proprietari: un `CREATE OR REPLACE` dal ruolo di
migrazione fallisce se la funzione non è sua.

---

### Test

* `db/pgtap/dbops/test-security-definer-search-path-v1.sql` — come le altre due funzioni di
  `postgres`, fissa esattamente `pg_catalog`, `public`, `pg_temp`.

---

### Note di migrazione

* 2025-11-14 — nasce come porta unica della generazione registrata.
* 2026-09-12 — il percorso di ricerca è fissato nella definizione.

---

{% include-markdown "signature-core.md" %}
