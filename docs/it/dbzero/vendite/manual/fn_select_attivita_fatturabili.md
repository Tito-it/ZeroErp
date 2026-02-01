## 📘 Documentazione Concettuale – Funzione `vendite.fn_select_attivita_fatturabili`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)   
> • [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)   
> • [config.tipi_doc_fiscale](/dbzero/config/tabelle/tipi_doc_fiscale)  
>
> **Approfondimento funzioni:**
>
> • [vendite.fn_execute_pipeline_step](/dbzero/vendite/funzioni/fn_execute_pipeline_step)   
> • [vendite.pr_run_lotto_pipeline](/dbzero/vendite/funzioni/pr_run_lotto_pipeline)   
>
---

### 🎯 Scopo Principale

(latest review 27-01-2026)
La funzione **`vendite.fn_select_attivita_fatturabili()`** seleziona le righe
**eleggibili** per la fatturazione e, se richiesto, le **locka** in modo atomico.

---

### ✅ Regole principali

* `competenza_mese` e` obbligatoria e viene normalizzata al primo del mese.
* `tipo_doc_fiscale_id` e` obbligatorio.
* Se `p_lock = true` allora `p_lock_batch_id` e` obbligatorio.
* Vengono escluse righe:
  * gia` fatturate,
  * sospese,
  * non approvate,
  * lockate.
* Rispetta `posticipa_al` e la regola di competenza su `competenza_mese`.
* Con `p_lock = true` usa `FOR UPDATE SKIP LOCKED` e aggiorna
  `lock_in_fatturazione` + `lock_batch_id`.
* `p_lock = false` equivale a una **dry-run**: nessuna scrittura, solo selezione.

---

### 🔍 Filtri opzionali

* `billing_account_id`
* `utility_id` (da billing_account)
* `valuta_id`
* `emittente_soggetto_ruolo_id` (da mapping BA → emittente)
* `area_geografica_id`
* `p_limit` limita il numero massimo di righe elaborate/lockate.(Accetta null=  no limite)

---

### ✅ Output

Ritorna le righe selezionate (o lockate) ordinate per `data_attivita`, `id`.

---

### 🧪 Esempi d’uso

**Dry-run (solo selezione)**

```sql
SELECT *
FROM vendite.fn_select_attivita_fatturabili(
  p_competenza_mese       => date '2026-01-01',
  p_tipo_doc_fiscale_id   => 1,
  p_lock                 => false,
  p_billing_account_id   => NULL,
  p_utility_id           => NULL,
  p_valuta_id            => NULL,
  p_emittente_soggetto_ruolo_id => NULL,
  p_limit                => 200
);
```

**Selezione + lock**

```sql
SELECT *
FROM vendite.fn_select_attivita_fatturabili(
  p_competenza_mese       => date '2026-01-01',
  p_tipo_doc_fiscale_id   => 1,
  p_lock_batch_id         => uuidv7(),
  p_lock                 => true,
  p_limit                => 200
);
```

---

{% include-markdown "signature-core.md" %}
