## 📘 Documentazione Concettuale – Funzione `vendite.fn_cambia_stato_ordine(bigint, varchar)`

> 👀 **Vedi anche**
>
> [vendite.ordini](/dbzero/vendite/tabelle/ordini) ·
> [config.transizioni_stati_ordini](/dbzero/config/tabelle/transizioni_stati_ordini) ·
> [vendite.fn_annulla_ordine](/dbzero/vendite/funzioni/fn_annulla_ordine) ·
> [vendite.fn_ordine_proietta_stato_evasione](/dbzero/vendite/funzioni/fn_ordine_proietta_stato_evasione) ·
> guida [Il modello del documento di vendita](/guide/modello-documento-di-vendita) §5, §6

### 🎯 Scopo
(25-10-2026 — brief `brief-modello-documento-vendita` §9, giro dell'ordine)

**Il verbo di stato dell'ordine.** Ogni cambio di stato che un operatore chiede su un
ordine passa da qui: la conferma (che è l'emissione dell'ordine) e l'annullo. Prima
l'ordine non aveva un verbo e lo stato lo scriveva il backend con un aggiornamento
diretto.

### Regole

* **Il permesso** lo dice la riga del passaggio nella matrice: la conferma e l'annullo
  di un ordine confermato chiedono l'azione `emetti_ordine`; l'annullo di una bozza
  chiede solo il permesso sul documento. Senza l'azione: `E_PERMESSO_NEGATO`.
* **I passaggi di processo** — l'evasione, fra confermato, parzialmente evaso ed
  evaso — non si chiedono qui (`E_DOC_PASSAGGIO_DI_PROCESSO`): li scrive la proiezione
  dell'evasione quando esce o torna indietro una bolla.
* **Le condizioni** del passaggio (la matrice, almeno una riga attiva alla conferma, le
  aliquote, i prezzi autorizzati, l'annullabilità) le giudica il guard di transizione
  dell'ordine, su qualunque strada cambi lo stato.
* **Il perimetro**: un ordine che l'operatore non vede è come inesistente
  (`E_ORD_NOT_FOUND`).
* Lo stato chiesto è il **codice** dello stato (`codice_interno`); uno stato che non c'è
  o è spento: `E_STATO_WORKFLOW_NON_TROVATO`.

### Chi la chiama

Il backend, per «Emetti» e per il cambio di stato; il verbo d'annullo
[`vendite.fn_annulla_ordine`](/dbzero/vendite/funzioni/fn_annulla_ordine), dopo aver
ritirato i legami; la fixture dei test. Lo stato si scrive solo da qui e dalla
proiezione dell'evasione: un aggiornamento diretto della colonna è rifiutato
(`E_DOC_STATO_SOLO_DAL_VERBO`).
