## 📘 Documentazione Concettuale – Funzione `pagamenti.trgfn_vendite_contabili_guard_ente_centro`

### 🎯 Scopo Principale
Validare la coerenza tra `centro_riscossione_id` della testata e
`ente_incasso_id` quando presente, e applicare i vincoli della compensazione.

### ✅ Regole applicate
* Se `ente_incasso_id` e` valorizzato, legge il `centro_riscossione_id` dell’ente.
* Blocca la scrittura se il centro dell’ente non coincide con quello della testata.
* Se `compensazione_id` e` valorizzato:
  * richiede `centro_riscossione.is_compensazione = true`
  * blocca la scrittura se la testata risulta gia` collegata a un lotto.

### 🔁 Quando si attiva
* `BEFORE INSERT OR UPDATE OF centro_riscossione_id, ente_incasso_id, compensazione_id`
  su `pagamenti.vendite_contabili`.

### ⚠️ Error handling
* In caso di incoerenza usa `script.fn_log_and_raise_error(...)`.

{% include-markdown "signature-core.md" %}
