## 📘 Documentazione Concettuale – Tabella `vendite.commesse_push_log`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.commesse](/dbzero/vendite/tabelle/commesse)  
> • [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)  
>
---

### 🎯 Scopo Principale

`vendite.commesse_push_log` traccia ogni esecuzione dell'orchestratore di push
sorgenti verso commesse/attivita` con un audit minimale ma operativo.

---

### 🧱 Campi chiave (semantica)

* **Run**: `run_at`, `dry_run`, `source_types`.
* **Esito**: `stato` (`COMPLETATO | PARZIALE | ERRORE`), `durata_ms`.
* **Dettaglio**: `risultato` (`jsonb` per handler: created/updated/skipped/errors).
* **Audit**: `data_insert`, `user_insert`, `data_update`, `user_update` (user reale via JWT).

---

### ✅ Regole principali

* Tabella **append-only** a grana run (non per singola riga sorgente).
* `stato` vincolato a `COMPLETATO`, `PARZIALE`, `ERRORE`.
* `durata_ms` opzionale ma non negativa.
* Indice su `run_at` per consultazione scheduler/audit recenti.

---

### 🔒 Concorrenza

La concorrenza e` gestita tramite `pg_try_advisory_lock`.
Non esistono tabelle di lock applicative e non e` previsto flag `is_running`.

---

### 🧩 Utilizzo previsto

* verificare esito run schedulati,
* diagnosticare errori per handler/sorgente,
* mantenere storico compatto dei run senza introdurre stato runtime persistente.

---

{% include-markdown "signature-core.md" %}
