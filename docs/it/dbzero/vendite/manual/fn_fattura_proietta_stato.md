## 📘 Documentazione Concettuale – Funzione `vendite.fn_fattura_proietta_stato(bigint, bigint)`

> 👀 **Vedi anche**
>
> [vendite.fatture](/dbzero/vendite/tabelle/fatture) ·
> [config.stati_doc_fiscale_transizioni](/dbzero/config/tabelle/stati_doc_fiscale_transizioni) ·
> [vendite.fn_sync_lotto_fatture_stato](/dbzero/vendite/funzioni/fn_sync_lotto_fatture_stato) ·
> guida [Il modello del documento di vendita](/guide/modello-documento-di-vendita) §5

### 🎯 Scopo
(27-10-2026 — brief `brief-modello-documento-vendita` §15, giro della fattura, F-1, Q-F3)

**Il verbo della fattura.** La fattura cambia stato con il suo lotto, ma anche da sola (domani,
per esempio, con l'esito dello SDI). Lo stato di una fattura si scrive solo da qui.

### Regole

* Oggi tutti i passaggi della fattura nella matrice sono di processo: li scrive la pipeline,
  che ne è la causa. Per questo il verbo non chiede un permesso.
* Lo stato che la fattura ha già: niente da fare.
* Un passaggio che la matrice segna come manuale non si scrive da qui
  (`E_LOTTO_PARAMETRO_NON_COERENTE`): sarà di un verbo con il permesso, quando l'esito SDI
  porterà passaggi manuali.
* La matrice la giudica il guard di transizione della fattura.

### Chi la chiama

[`vendite.fn_sync_lotto_fatture_stato`](/dbzero/vendite/funzioni/fn_sync_lotto_fatture_stato) (la
fattura segue il lotto), [`vendite.fn_numera_fattura_opz_emessa`](/dbzero/vendite/funzioni/fn_numera_fattura_opz_emessa),
[`vendite.fn_close_giornaliero_lotto`](/dbzero/vendite/funzioni/fn_close_giornaliero_lotto); la
fixture dei pgTAP `dbops.fn_pgtap_porta_a_stato`.

---

{% include-markdown "signature-core.md" %}
