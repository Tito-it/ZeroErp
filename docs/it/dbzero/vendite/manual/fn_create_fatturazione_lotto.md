## 📘 Documentazione Concettuale – Funzione `vendite.fn_create_fatturazione_lotto`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)   
> • [config.utilities](/dbzero/config/tabelle/utilities)   
> • [config.tipi_doc_fiscale](/dbzero/config/tabelle/tipi_doc_fiscale)   
> • [vendite.tipi_doc_fiscale_registri](/dbzero/vendite/manual/tipi_doc_fiscale_registri)   
> • [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_get_or_create_lotto](/dbzero/vendite/funzioni/fn_get_or_create_lotto)   
>
### 🎯 Scopo Principale
(latest review 12-11-2026)
La funzione **`vendite.fn_create_fatturazione_lotto()`** crea un lotto di
fatturazione con parametri coerenti (competenza, utility, tipo documento, BA).
Lo stato non lo sceglie: il lotto nasce nello stato iniziale del vocabolario
[`config.stati_doc_fiscale`](/dbzero/config/manual/stati_doc_fiscale), che mette
il trigger della nascita.

---

### Regole applicate

* `competenza_mese` e` **obbligatoria** e viene normalizzata al primo del mese.
* `utility_id` e` obbligatoria: se `billing_account_id` e` presente viene ricavata da BA.
* `tipo_doc_fiscale_id` e` **obbligatorio** e deve essere attivo.
* Deve esistere il mapping `tipo_doc_fiscale → registro` in `vendite.tipi_doc_fiscale_registri`.
* `stato_doc_fiscale_id` non è nell'`INSERT`: lo mette il trigger
  `trg_fatturazione_lotti_a05_stato_iniziale_ins`
  ([`script.trgfn_doc_stato_iniziale`](/dbzero/script/funzioni/trgfn_doc_stato_iniziale)),
  leggendo la colonna `iniziale` del vocabolario. Che lo stato iniziale si applichi
  al lotto lo garantisce un vincolo del vocabolario, non questa funzione.
* `lock_batch_id` viene generato se non fornito.

---

### Output

Ritorna l’`id` del lotto creato in `vendite.fatturazione_lotti`.

---

{% include-markdown "signature-core.md" %}
