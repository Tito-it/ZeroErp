## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_fatture_guard_stato`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [config.stati_doc_fiscale_transizioni](/dbzero/config/tabelle/stati_doc_fiscale_transizioni)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_set_fatturazione_lotto_stato](/dbzero/vendite/funzioni/fn_set_fatturazione_lotto_stato)  
> • [vendite.trgfn_fatture_numerata_non_annulabile](/dbzero/vendite/funzioni/trgfn_fatture_numerata_non_annulabile)  
>
🎯 Scopo Principale

(latest review 24-01-2026)
La funzione **`vendite.trgfn_fatture_guard_stato()`** controlla le transizioni
tra stati documento sulle fatture, bloccando quelle non ammesse.

---

### Regola applicata

* Trigger `BEFORE UPDATE OF stato_doc_fiscale_id` su `vendite.fatture`.
* Verifica la transizione in `config.stati_doc_fiscale_transizioni`.
* Se lo stato non e` applicabile o la transizione non e` ammessa → errore.
* Lotto **GIORNALIERO**: vietata retrocessione di stato.

---

{% include-markdown "signature-core.md" %}
