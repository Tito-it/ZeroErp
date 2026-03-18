## 📘 Documentazione Concettuale – Funzione `vendite.fn_resolve_stato_esecuzione`

---
### 🎯 Scopo Principale
(latest review 22-02-2026)
Helper condiviso per risolvere in modo uniforme il valore di `stato_esecuzione` nei flussi `fatturazione_lotti` e `attivita_fatturabili`.

---

### Regole applicate

* Priorita` applicata:
  * `esclusa=true` -> mantiene lo stato corrente.
  * `critical=true` -> forza `ERRORE`.
  * `fatturato=true` -> forza `COMPLETED`.
* Mapping sorgente:
  * `IN_ESECUZIONE -> RUNNING`
  * `COMPLETATO -> COMPLETED`
  * `PENDING|RUNNING|COMPLETED|ERRORE` pass-through
* Se `p_stato_source` e` vuoto/non valido, usa `p_default_stato_esecuzione` (fallback `PENDING`).

---

### Output

Ritorna il valore `stato_esecuzione` risolto (`varchar`) tra:

* `PENDING`
* `RUNNING`
* `COMPLETED`
* `ERRORE`

---

{% include-markdown "signature-core.md" %}
