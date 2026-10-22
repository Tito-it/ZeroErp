## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_or_create_lotto`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_create_fatturazione_lotto](/dbzero/vendite/funzioni/fn_create_fatturazione_lotto)     
> • [vendite.fn_resolve_lotto_utility_emittente](/dbzero/vendite/funzioni/fn_resolve_lotto_utility_emittente)
>
### 🎯 Scopo Principale
(latest review 22-02-2026)
La funzione **`vendite.fn_get_or_create_lotto()`** recupera un lotto esistente
(o lo crea se assente) garantendo la coerenza dei parametri di richiesta.

---

### Regole applicate

* `tipo_lotto` obbligatorio (MASSIVO | GIORNALIERO).
* Se `p_lotto_id` e` valorizzato:
  * verifica l’esistenza del lotto;
  * valida la coerenza di `competenza_mese`, `utility_id`, `tipo_doc_fiscale_id`, `billing_account_id`, `emittente_soggetto_ruolo_id`, `tipo_lotto`.
  * ⭐ **l'emittente di un lotto esistente è quello del lotto** (rev 2026-10-22): si confronta
    solo l'emittente che il chiamante **ha indicato**, esplicito o tramite il BA. Il rilancio
    col solo `lotto_id` (il FE manda solo quello, su «Avanza» e dopo un ERRORE) non lo
    confronta con niente. Prima il risolutore, senza BA, ripiegava sull'emittente
    **predefinito** e ogni lotto di un altro emittente veniva rifiutato. Vale anche per il
    lotto ritrovato dal `lock_batch_id`.
  * blocca il riuso solo se il lotto e` in `IN_ESECUZIONE` **e** `stato_operativo <> APERTO`.
* Se `p_lock_batch_id` e` valorizzato e non esiste un lotto, ne crea uno nuovo.
* Se non e` presente nessun riferimento, delega a `fn_create_fatturazione_lotto`. Solo qui,
  per un lotto **nuovo** senza BA e senza emittente, vale il ripiego sull'emittente
  predefinito, e solo qui si pretende che l'emittente del lotto sia attivo.
* La risoluzione/validazione di `utility_id` + `emittente_soggetto_ruolo_id` e` centralizzata nell'helper condiviso `vendite.fn_resolve_lotto_utility_emittente(...)`, riusato anche dal dominio `attivita_fatturabili`.

---

### Output

Ritorna l’`id` del lotto esistente o creato.

---

{% include-markdown "signature-core.md" %}
