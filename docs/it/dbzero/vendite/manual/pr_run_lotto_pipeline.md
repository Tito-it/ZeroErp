## 📘 Documentazione Concettuale – Procedura `vendite.pr_run_lotto_pipeline`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)  
> • [vendite.fatturazione_pipeline](/dbzero/vendite/manual/fatturazione_pipeline)  
> • [vendite.fatturazione_lotti_log](/dbzero/vendite/tabelle/fatturazione_lotti_log)  
>
> **Approfondimento funzioni:**
>
> • [vendite.fn_get_or_create_lotto](/dbzero/vendite/funzioni/fn_get_or_create_lotto)   
> • [vendite.fn_set_fatturazione_lotto_stato](/dbzero/vendite/funzioni/fn_set_fatturazione_lotto_stato)   
> • [vendite.fn_execute_pipeline_step](/dbzero/vendite/funzioni/fn_execute_pipeline_step)   
> • [vendite.fn_log_pipeline_fase](/dbzero/vendite/funzioni/fn_log_pipeline_fase)   
>
---

### 🎯 Scopo Principale

(latest review 28-01-2026)  
La procedura **`vendite.pr_run_lotto_pipeline()`** esegue la pipeline configurabile
del lotto: imposta lo **stato job**, aggiorna lo **stato lotto** per ogni step e
invoca l’esecuzione dei task (filtrati per `tipo_lotto`).

---

### ✅ Regole principali

* `lotto_id` opzionale: se assente (o = 0), la procedura crea/recupera il lotto dai parametri.
* `stato_lotto` viene impostato a `IN_ESECUZIONE` all’avvio e `COMPLETATO` a fine job.
* Per ogni step:
  * aggiorna `stato_doc_fiscale_id` del lotto,
  * scrive un log `status=I` con `fase`,
  * esegue i task definiti in `processi`.
* Lotto **GIORNALIERO**: alla transizione a `INVIATA`:
  * `stato_operativo` → `CHIUSO`
  * tutte le fatture del lotto → `INVIATA`
* In caso di errore: `stato_lotto = ERRORE` e rilancio dell’eccezione.
  
* **Regola di sicurezza: i task devono usare **solo `lotto_id`** come input; i  parametri operativi vengono letti dal lotto (o tabelle collegate).**

---

### ✅ Output

Nessun output (PROCEDURE). Gli esiti sono tracciati su `fatturazione_lotti_log`.

---

### 🧪 Esempio

```sql
CALL vendite.pr_run_lotto_pipeline(
  p_lotto_id := 123,
  p_dry_run := true
);
```

```sql
CALL vendite.pr_run_lotto_pipeline(
  p_lotto_id := NULL,
  p_competenza_mese := date '2026-01-01',
  p_tipo_doc_fiscale_id := 1,
  p_utility_id := NULL,
  p_billing_account_id := NULL,
  p_lock_batch_id := uuidv7(),
  p_meta := '{}'::jsonb,
  p_dry_run := true
);
```

---

{% include-markdown "signature-core.md" %}
