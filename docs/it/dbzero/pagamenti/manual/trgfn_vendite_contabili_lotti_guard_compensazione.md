## 📘 Documentazione Concettuale – Funzione `pagamenti.trgfn_vendite_contabili_lotti_guard_compensazione`

### 🎯 Scopo Principale
Impedire l'associazione di testate contabili di compensazione alla tabella
ponte dei lotti (`pagamenti.vendite_contabili_lotti`).

### ✅ Regole applicate
* Se la testata (`contabile_id`) ha `compensazione_id` valorizzato:
  * blocca `INSERT/UPDATE` del link lotto-contabile.

### 🔁 Quando si attiva
* `BEFORE INSERT OR UPDATE OF contabile_id`
  su `pagamenti.vendite_contabili_lotti`.

### ⚠️ Error handling
* In caso di violazione usa `script.fn_log_and_raise_error(...)`.

{% include-markdown "signature-core.md" %}
