## 📘 Documentazione Concettuale – Funzione `pagamenti.fn_get_or_create_vendite_contabile`

### 🎯 Scopo Principale
Recuperare una testata contabile vendite esistente oppure crearne una nuova,
con possibilita` di collegarla al lotto fatturazione tramite tabella ponte.

### Regole principali
* Valida parametri obbligatori (`centro_riscossione_id`, `data_contabile`, stato).
* Supporta `p_compensazione_id` opzionale:
  * se valorizzato, identifica in modo univoco la testata contabile
  * non e` compatibile con `p_lotto_id`.
* Risolve lo stato da `pagamenti.vendite_contabili_stati.codice_interno`.
* Se trova una testata coerente, la riusa.
* Se non la trova, crea una nuova testata.
* Se `p_lotto_id` e` valorizzato, inserisce il link in `pagamenti.vendite_contabili_lotti`.

### Esempio d’uso
```sql
SELECT pagamenti.fn_get_or_create_vendite_contabile(
  p_centro_riscossione_id => 1,
  p_data_contabile => current_date,
  p_ente_incasso_id => NULL,
  p_compensazione_id => NULL,
  p_lotto_id => 123,
  p_codice_stato_interno => 'BOZZA'
);
```

{% include-markdown "signature-core.md" %}
