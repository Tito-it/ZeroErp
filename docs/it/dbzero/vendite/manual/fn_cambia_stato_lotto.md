## 📘 Documentazione Concettuale – Funzione `vendite.fn_cambia_stato_lotto(bigint, varchar)`

> 👀 **Vedi anche**
>
> [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti) ·
> [config.stati_doc_fiscale_transizioni](/dbzero/config/tabelle/stati_doc_fiscale_transizioni) ·
> [vendite.fn_riporta_lotto_a_draft](/dbzero/vendite/funzioni/fn_riporta_lotto_a_draft) ·
> [vendite.fn_annulla_lotto_da_draft](/dbzero/vendite/funzioni/fn_annulla_lotto_da_draft) ·
> [vendite.fn_lotto_proietta_stato_step](/dbzero/vendite/funzioni/fn_lotto_proietta_stato_step) ·
> guida [Il modello del documento di vendita](/guide/modello-documento-di-vendita) §5, §6

### 🎯 Scopo
(27-10-2026 — brief `brief-modello-documento-vendita` §15, giro della fattura)

**Il verbo dei pulsanti del lotto.** La fattura non ha pulsanti suoi: lo stato lo guida il lotto
di fatturazione. Questo è il verbo dei passaggi che l'operatore chiede a mano sul lotto:
riportarlo in bozza e annullarlo mentre è in bozza.

### Regole

* Il permesso sta sulla riga del passaggio: «riporta in bozza» chiede `numera_fatture_lotti`,
  la stessa azione di «numera» (chi può numerare può anche tornare indietro finché le fatture
  non hanno un numero); l'annullo della bozza chiede solo il permesso sui lotti.
* Un passaggio che fa il sistema (l'avanzamento della pipeline) non si chiede da qui
  (`E_DOC_PASSAGGIO_DI_PROCESSO`); lo stato che il lotto ha già: `E_DOC_GIA_NELLO_STATO`.
* «Numera» è una riga manuale, ma lo stato lo scrive il giro della pipeline, quando il lavoro
  accodato dal pulsante gira: [`vendite.fn_lotto_proietta_stato_step`](/dbzero/vendite/funzioni/fn_lotto_proietta_stato_step).
* Non fa la pulizia (fatture cancellate, attività liberate): la fanno le funzioni che lo
  chiamano. Chiamato da solo su un lotto con fatture avanti, il passaggio lo rifiuta la
  coerenza fra lotto e fatture.

### Chi la chiama

[`vendite.fn_riporta_lotto_a_draft`](/dbzero/vendite/funzioni/fn_riporta_lotto_a_draft) e
[`vendite.fn_annulla_lotto_da_draft`](/dbzero/vendite/funzioni/fn_annulla_lotto_da_draft), in
fondo, dopo la pulizia; la fixture dei pgTAP `dbops.fn_pgtap_porta_a_stato`.

---

{% include-markdown "signature-core.md" %}
