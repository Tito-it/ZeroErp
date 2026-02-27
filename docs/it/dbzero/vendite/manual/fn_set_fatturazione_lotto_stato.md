## 📘 Documentazione Concettuale – Funzione `vendite.fn_set_fatturazione_lotto_stato`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)  
>
> **Approfondimento funzioni:**
>
> • [vendite.fn_log_pipeline_fase](/dbzero/vendite/funzioni/fn_log_pipeline_fase)  
>
---

### 🎯 Scopo Principale

(latest review 27-01-2026)  
La funzione **`vendite.fn_set_fatturazione_lotto_stato()`** aggiorna lo **stato
job** del lotto di fatturazione e allinea lo **stato operativo**.

---

### ✅ Regole principali

* Stati ammessi: `IN_ESECUZIONE`, `COMPLETATO`, `ERRORE`.
* Transizioni consentite:
  * `IN_ESECUZIONE` → `COMPLETATO` | `ERRORE`
  * `ERRORE` → `IN_ESECUZIONE` (reset)
  * `COMPLETATO` = stato finale (nessun ritorno)
* MASSIVO: `COMPLETATO` → `stato_operativo = CHIUSO`
* GIORNALIERO: `stato_operativo` viene gestito al passaggio a INVIATA
* Se lo stato richiesto coincide con quello corrente, la funzione non fa nulla.
* Se `p_note` e` valorizzato, viene salvata in `meta.note_stato`.

---

### ✅ Output

Nessun output (RETURN void). In caso di transizione non ammessa viene sollevato
errore con log applicativo.

---

### 🧪 Esempi d’uso

```sql
SELECT vendite.fn_set_fatturazione_lotto_stato(123, 'IN_ESECUZIONE', 'Avvio job');
SELECT vendite.fn_set_fatturazione_lotto_stato(123, 'COMPLETATO', 'Processo completato');
```

---

{% include-markdown "signature-core.md" %}
