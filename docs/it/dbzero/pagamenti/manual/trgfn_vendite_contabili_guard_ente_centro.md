## 📘 Documentazione Concettuale – Funzione `pagamenti.trgfn_vendite_contabili_guard_ente_centro`
### 🎯 Scopo Principale
Validare la coerenza tra `centro_riscossione_id` della testata e
`ente_incasso_id` quando presente.

### Regole applicate
* Se `ente_incasso_id` e` valorizzato, legge il `centro_riscossione_id` dell’ente.
* Blocca la scrittura se il centro dell’ente non coincide con quello della testata.
> ⚠️ **Rev 2026-08-22 (lotto 7, D15-e): il ramo delle compensazioni non c'è più.**
> Si apriva su `NEW.compensazione_id`, e quella colonna è sparita girando il verso
> del legame: la contabile non sa più di essere nata da un atto, lo sa l'atto.
> ⭐ Le due regole **non sono state perse, hanno cambiato casa** — e sono andate
> dove il dato che le rende decidibili esiste davvero:
>
> | Regola | Dove vive adesso |
> | --- | --- |
> | il centro dev'essere quello di compensazione | `trgfn_sistemazioni_guard_dati` |
> | la contabile non si aggancia a un lotto | `trgfn_vendite_contabili_lotti_guard_sistemazione` |
>
> *Un controllo che scatta quando l'informazione non c'è ancora non è un
> presidio: alla nascita della distinta nessun atto la cita.*

⛔ *(storico, non più valido)* Se `compensazione_id` era valorizzato:
  * richiedeva `centro_riscossione.is_compensazione = true`
  * blocca la scrittura se la testata risulta gia` collegata a un lotto.

### Quando si attiva
* `BEFORE INSERT OR UPDATE OF centro_riscossione_id, ente_incasso_id`
  ⚠️ La lista è stata **ricreata**: una lista di colonne crea una dipendenza vera
  nel catalogo, e con `compensazione_id` dentro il `DROP COLUMN` sarebbe fallito.
  ⭐ Il corpo di una `plpgsql` non crea dipendenze, la lista di un trigger **sì**.
  su `pagamenti.vendite_contabili`.

### ⚠️ Error handling
* In caso di incoerenza usa `script.fn_log_and_raise_error(...)`.

{% include-markdown "signature-core.md" %}
