## 📘 Documentazione Concettuale – Funzione `vendite.fn_lotto_proietta_stato_step(bigint, bigint)`

> 👀 **Vedi anche**
>
> [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti) ·
> [vendite.fatturazione_pipeline](/dbzero/vendite/tabelle/fatturazione_pipeline) ·
> [vendite.fn_cambia_stato_lotto](/dbzero/vendite/funzioni/fn_cambia_stato_lotto) ·
> [vendite.fn_sync_lotto_fatture_stato](/dbzero/vendite/funzioni/fn_sync_lotto_fatture_stato) ·
> guida [Il modello del documento di vendita](/guide/modello-documento-di-vendita) §5 (i passaggi di processo)

### 🎯 Scopo
(27-10-2026 — brief `brief-modello-documento-vendita` §15, giro della fattura, P-2)

**Il giro della pipeline porta il lotto nello stato del suo step.** A ogni step il runner del
backend avanza il lotto (bozza → emessa → definitiva → inviata). Prima lo faceva con un
`UPDATE`; ora chiama questa funzione, negli stessi momenti: il processo dei lotti non cambia.

### Regole

* È un passaggio di processo: lo scrive la causa (il giro), senza chiedere un permesso. Il
  permesso di «numera» si chiede quando l'operatore preme il pulsante.
* Lo stato che il lotto ha già: niente da fare.
* Lo stato chiesto dev'essere quello di uno step attivo della pipeline per il tipo del lotto
  (massivo, giornaliero), e non lo stato iniziale: tornare in bozza è «riporta in bozza», con la
  sua pulizia. Altrimenti `E_LOTTO_PARAMETRO_NON_COERENTE`.
* Matrice e fermo del lotto li giudica il guard di transizione del lotto.
* Le fatture del lotto le allinea poi [`vendite.fn_sync_lotto_fatture_stato`](/dbzero/vendite/funzioni/fn_sync_lotto_fatture_stato).

### Chi la chiama

Il runner della pipeline del backend (al posto di `update_lotto_stato_doc`);
[`vendite.fn_close_giornaliero_lotto`](/dbzero/vendite/funzioni/fn_close_giornaliero_lotto); la
fixture dei pgTAP `dbops.fn_pgtap_porta_a_stato`.

---

{% include-markdown "signature-core.md" %}
