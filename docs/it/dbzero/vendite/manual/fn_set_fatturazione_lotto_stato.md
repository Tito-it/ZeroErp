## 📘 Documentazione Concettuale – Funzione `vendite.fn_set_fatturazione_lotto_stato`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)  
>
---

### 🎯 Scopo Principale

(latest review 27-01-2026)  
La funzione **`vendite.fn_set_fatturazione_lotto_stato()`** aggiorna lo **stato
operativo** del lotto di fatturazione, applicando regole minime di transizione.

---

### ✅ Regole principali

* Stati ammessi: `IN_ESECUZIONE`, `COMPLETATO`, `ERRORE`.
* Transizioni consentite:
  * `IN_ESECUZIONE` → `COMPLETATO` | `ERRORE`
  * `ERRORE` → `IN_ESECUZIONE` (reset)
  * `COMPLETATO` = stato finale (nessun ritorno)
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
