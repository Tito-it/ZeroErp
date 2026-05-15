## 📘 Documentazione Concettuale – Trigger Function `vendite.trgfn_contratti_righe_lock_post_attivazione()`

> 👀 **Vedi anche**
>
> Tabelle correlate:
>
> [vendite.contratti_righe](/dbzero/vendite/tabelle/contratti_righe) — tabella guardata
> [vendite.contratti](/dbzero/vendite/tabelle/contratti) — contratto padre (stato)
>
> Funzioni correlate:
>
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)
> [vendite.trgfn_contratti_lock_post_attivazione](/dbzero/vendite/funzioni/trgfn_contratti_lock_post_attivazione) — lock simmetrico sulla testata

La trigger function **`vendite.trgfn_contratti_righe_lock_post_attivazione()`** blocca qualsiasi INSERT, UPDATE o DELETE su `contratti_righe` quando il contratto padre è in stato ATTIVO.

---

### 🎯 Scopo Principale

Le eccezioni di un contratto attivo (OVERRIDE, ESCLUSIONE, AGGIUNTA) sono **immutabili post-attivazione** (§3-bis-A). Questo enforcement avviene a livello DB per garantire il blocco anche da psql diretto, script di manutenzione o chiamate API non validate. Il lock è simmetrico a quello sulla testata (`trgfn_contratti_lock_post_attivazione`).

---

### Logica

Legge lo stato del contratto padre via JOIN su `vendite.contratti` → `config.stati_doc_contratti`. Se `codice_interno = 'ATTIVO'`: raise `E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE`.

Gestione `TG_OP`:
* `INSERT` / `UPDATE`: usa `NEW.contratto_id` — ritorna `NEW`.
* `DELETE`: usa `OLD.contratto_id` — ritorna `OLD`.

Il contesto JSONB del log include `contratto_id`, `articolo_id` e `operazione` (INSERT/UPDATE/DELETE).

---

### Applicazione

Trigger creato dalla migration `20260515-14`:

* **`trg_contratti_righe_a10_lock_post_attivazione_ins_upd_dlt`** su `vendite.contratti_righe`
* Timing: **BEFORE INSERT OR UPDATE OR DELETE**
* Fase: **_a10_**
* Scope: **FOR EACH ROW**

---

### Codice errore sollevato

**`E_CONTRATTO_CAMPI_BLOCCATI_POST_ATTIVAZIONE`** (id 452) — `config.messaggi_errore`.

HTTP mapping (BE): `409 Conflict`.

---

### Ordine rispetto agli altri trigger _a10_ su contratti_righe

Ordine lessicografico dei trigger BEFORE su `vendite.contratti_righe`:

| Trigger | Evento | Quando scatta |
| --- | --- | --- |
| `trg_contratti_righe_a10_guard_aggiunta_fuori_listino_ins_upd` | INS/UPD | WHEN tipo_eccezione = 'AGGIUNTA' |
| `trg_contratti_righe_a10_lock_post_attivazione_ins_upd_dlt` | INS/UPD/DLT | Contratto padre ATTIVO |
| `trg_contratti_righe_a10_qta_from_operativa_ins_upd` | INS/UPD | Sempre |

Il lock scatta **prima** di `qta_from_operativa` e degli AFTER trigger, quindi blocca l'operazione prima di qualsiasi elaborazione.

{% include-markdown "signature-core.md" %}

---
