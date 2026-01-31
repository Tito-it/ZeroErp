## 📘 Documentazione Concettuale – Funzione `vendite.fn_sync_fattura_critical`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [vendite.fatture_log](/dbzero/vendite/manual/fatture_log)  
>
> **Approfondimento funzioni:**
>
> • [vendite.fn_log_lotto_esito_fatture](/dbzero/vendite/funzioni/fn_log_lotto_esito_fatture)  
> • [vendite.fn_sync_lotto_fatture_stato](/dbzero/vendite/funzioni/fn_sync_lotto_fatture_stato)  
>
---

### 🎯 Scopo Principale

(latest review 29-01-2026)  
La funzione **`vendite.fn_sync_fattura_critical()`** aggiorna il flag
`fatture.critical` in base ai log attivi della fattura.

---

### ✅ Regole principali

* Se esiste almeno un log **critical** (`status='C'`) non disabilitato,
  `fatture.critical = true`.
* I log disabilitati non vengono considerati.
* I warning non impostano `critical`.
* Uso previsto: durante l’esecuzione della pipeline o quando si vuole
  sincronizzare lo stato `critical` con i log correnti.

---

### ✅ Output

Nessun output (RETURN void).

---

{% include-markdown "signature-core.md" %}
