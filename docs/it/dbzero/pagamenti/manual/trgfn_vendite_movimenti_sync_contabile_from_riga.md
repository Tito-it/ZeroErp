## 📘 Documentazione Concettuale – Funzione `pagamenti.trgfn_vendite_movimenti_sync_contabile_from_riga`

### 🎯 Scopo Principale
Mantenere coerenti `contabile_id`, `fattura_id` e `billing_account_id`
su `pagamenti.vendite_movimenti` quando viene usato il riferimento a riga
(`contabile_riga_id`).

### Regole applicate
* Se `contabile_riga_id` e` valorizzato, legge dalla riga `pagamenti.vendite_contabili_righe`:
  `contabile_id`, `fattura_id`, `billing_account_id`.
* Se uno dei tre valori e` passato e diverso dal derivato, blocca la scrittura.
* In caso coerente, imposta `NEW.contabile_id`, `NEW.fattura_id`,
  `NEW.billing_account_id` ai valori derivati.

### Quando si attiva
* `BEFORE INSERT OR UPDATE OF contabile_riga_id, contabile_id, fattura_id, billing_account_id`
  su `pagamenti.vendite_movimenti`.

### ⚠️ Error handling
* In caso di incoerenza usa `script.fn_log_and_raise_error(...)`.

{% include-markdown "signature-core.md" %}
