## 📘 Documentazione Concettuale – Funzione `vendite.fn_log_lotto_esito_fatture`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)  
> • [vendite.fatturazione_lotti_log](/dbzero/vendite/tabelle/fatturazione_lotti_log)  
> • [vendite.fatture_log](/dbzero/vendite/manual/fatture_log)  
>
---

### 🎯 Scopo Principale

(latest review 29-01-2026)  
La funzione **`vendite.fn_log_lotto_esito_fatture()`** registra un log di
esito lotto dedotto dai log fatture associate al lotto.

---

### ✅ Regole principali

* Se esiste almeno un log **critical** attivo, lo status lotto è `C`.
* Se non ci sono critical ma esistono warning, lo status lotto è `W`.
* Se non esistono log attivi, lo status lotto è `I`.
* I log disabilitati non vengono considerati.
* Uso previsto: durante l’esecuzione della pipeline o quando si vuole
  riallineare l’esito lotto ai log fatture correnti.
* Il log generato include `tipo_lotto` e `stato_operativo` del lotto.

---

### ✅ Output

Nessun output (RETURN void).

---

{% include-markdown "signature-core.md" %}
