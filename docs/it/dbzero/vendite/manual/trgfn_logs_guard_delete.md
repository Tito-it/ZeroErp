## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_logs_guard_delete`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatture_log](/dbzero/vendite/tabelle/fatture_log)  
> • [vendite.fatturazione_lotti_log](/dbzero/vendite/tabelle/fatturazione_lotti_log)  
>
### 🎯 Scopo Principale
(latest review 20-02-2026)  
La funzione trigger **`vendite.trgfn_logs_guard_delete()`** blocca la cancellazione
diretta dei log funzionali (`fatture_log`, `fatturazione_lotti_log`) salvo
abilitazione esplicita di manutenzione.

---

### Regole principali

* Trigger `BEFORE DELETE` su:
  * `vendite.fatture_log`
  * `vendite.fatturazione_lotti_log`
* `DELETE` consentito solo se almeno una delle GUC è attiva:
  * `zeroerp.maintenance_allow_delete_logs = on`
  * `zeroerp.maintenance_reset_lotto_draft = on` (compatibilità reset tecnico)
* In assenza GUC attiva, la funzione alza errore bloccante.

---

### Output

Nessun output funzionale (trigger guard: ritorna `OLD` in caso consentito).

---

### Utilizzo previsto

Usata come guardrail per evitare cancellazioni accidentali dei log;
la pulizia è ammessa solo in processi tecnici controllati.

---

{% include-markdown "signature-core.md" %}
