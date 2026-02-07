## 📘 Documentazione Concettuale – Funzione `vendite.fn_execute_pipeline_step`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.fatturazione_pipeline](/dbzero/vendite/manual/fatturazione_pipeline)  
> • [vendite.fatturazione_lotti_log](/dbzero/vendite/tabelle/fatturazione_lotti_log)  
>
> **Approfondimento funzioni:**
>
> • [vendite.fn_select_attivita_fatturabili](/dbzero/vendite/funzioni/fn_select_attivita_fatturabili)   
> • [vendite.fn_log_pipeline_fase](/dbzero/vendite/funzioni/fn_log_pipeline_fase)   
>
---

### 🎯 Scopo Principale

(latest review 07-02-2026)  
(Deprecate-trasferite in django)  
La funzione **`vendite.fn_execute_pipeline_step()`** esegue i task definiti
nel JSON `processi` (o `rollback`) della pipeline per lo step corrente.

---

### ✅ Regole principali

* Richiede `lotto_id` e `stato_doc_fiscale_id`.
* Legge i task da `vendite.fatturazione_pipeline`.
* Scrive un log `status=I` per ogni task con dettaglio in `meta`.
* Non esegue SQL arbitrario: i task ammessi sono controllati tramite whitelist.
* Task supportati (iniziali): `select_attivita`, `noop`, `log_only`.
* E` possibile indicare un override `fn` nei `params` del task, ma solo se
  la funzione e` esplicitamente ammessa (whitelist interna).
* Con `p_dry_run = true` logga solo le fasi senza eseguire i task.

---

### ✅ Output

Nessun output (RETURN void). In caso di task non supportato viene sollevato
errore con log applicativo.

---

### 🧪 Esempio

```sql
SELECT vendite.fn_execute_pipeline_step(
  p_lotto_id => 123,
  p_stato_doc_fiscale_id => 1,
  p_rollback => false,
  p_dry_run => true
);
```

---

{% include-markdown "signature-core.md" %}
