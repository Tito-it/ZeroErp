## 📘 Documentazione Concettuale – Funzione `pagamenti.trgfn_vendite_movimenti_sync_contabile_from_riga`

### 🎯 Scopo Principale
Mantenere coerente `contabile_id` su `pagamenti.vendite_movimenti` quando
viene usato il riferimento a riga (`contabile_riga_id`).

### ✅ Regole applicate
* Se `contabile_riga_id` e` valorizzato, legge `contabile_id` dalla riga `pagamenti.vendite_contabili_righe`.
* Se `contabile_id` e` passato e diverso da quello derivato, blocca la scrittura.
* In caso coerente, imposta `NEW.contabile_id` al valore derivato.

### 🔁 Quando si attiva
* `BEFORE INSERT OR UPDATE OF contabile_riga_id, contabile_id`
  su `pagamenti.vendite_movimenti`.

### ⚠️ Error handling
* In caso di incoerenza usa `script.fn_log_and_raise_error(...)`.

{% include-markdown "signature-core.md" %}
