## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_fatturazione_lotti_guard_stato`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)  
> • [config.stati_doc_fiscale_transizioni](/dbzero/config/tabelle/stati_doc_fiscale_transizioni)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_set_fatturazione_lotto_stato](/dbzero/vendite/funzioni/fn_set_fatturazione_lotto_stato)  
>
🎯 Scopo Principale

(latest review 24-01-2026)
La funzione **`vendite.trgfn_fatturazione_lotti_guard_stato()`** controlla le
transizioni tra stati documento sui lotti di fatturazione.

---

### Regola applicata

* Trigger `BEFORE UPDATE OF stato_doc_fiscale_id` su `vendite.fatturazione_lotti`.
* Verifica la transizione in `config.stati_doc_fiscale_transizioni`.
* Se `config.stati_doc_fiscale_transizioni.meta.tipo_lotto` e` valorizzato,
  la transizione e` ammessa solo per lotti con lo stesso `tipo_lotto`.
* Se lo stato non e` applicabile o la transizione non e` ammessa → errore.

> Nota: il blocco puo` essere **bypassato** solo in contesti di manutenzione
> tramite GUC `zeroerp.maintenance_reset_lotto_draft = on` (reset tecnico lotto DRAFT).

---

{% include-markdown "signature-core.md" %}
