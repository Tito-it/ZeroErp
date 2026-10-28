## 📘 Documentazione Concettuale – Funzione `vendite.fn_annulla_offerta(bigint, text, integer)`

> 👀 **Vedi anche**
>
> [vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali) ·
> [vendite.fn_cambia_stato_offerta](/dbzero/vendite/funzioni/fn_cambia_stato_offerta) ·
> [vendite.fn_documento_legami](/dbzero/vendite/funzioni/fn_documento_legami) ·
> [script.fn_check_offerta_annullabile](/dbzero/script/funzioni/fn_check_offerta_annullabile) ·
> guida [Il modello del documento di vendita](/guide/modello-documento-di-vendita) §8

### 🎯 Scopo
(26-10-2026 — brief `brief-modello-documento-vendita` §13, giro dell'offerta)

**Il verbo d'annullo dell'offerta**, come quello degli altri documenti: prima ciò che vieta,
poi la conferma dei legami, poi lo stato.

### Regole

1. **Ciò che vieta**: un'offerta da cui vive un contratto o un ordine non annullato non si
   annulla (`E_OFFERTA_ANNULLO_CON_DOCUMENTI_VIVI`): prima si annulla quel documento.
2. **La conferma**: annullare l'ultima revisione viva di un'offerta fa tornare **emessa** la
   revisione precedente. È un legame (lo elenca
   [`vendite.fn_documento_legami`](/dbzero/vendite/funzioni/fn_documento_legami)): chi annulla
   dichiara quanti legami ha visto (`p_legami_confermati`), e se non corrispondono l'annullo è
   rifiutato con `E_DOC_ANNULLO_CON_LEGAMI`. Senza legami non c'è niente da confermare.
3. **Lo stato**, dal verbo di stato
   [`vendite.fn_cambia_stato_offerta`](/dbzero/vendite/funzioni/fn_cambia_stato_offerta), con la
   **motivazione**, che per l'annullo è obbligatoria, e con l'azione `emetti_offerta` se l'offerta
   era accettata. La revisione precedente torna emessa da sé, dalla proiezione delle revisioni
   vive.

Tutto in una transazione. Ritorna il numero di legami confermati (0 se non ce n'erano). Un'offerta
che l'operatore non vede è come inesistente (`E_OFFERTA_NON_TROVATA`).

### Chi la chiama

Il backend, alla conferma dell'annullo, dopo aver mostrato i legami.
