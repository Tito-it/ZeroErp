## 📘 Documentazione Concettuale – Funzione `vendite.fn_cambia_stato_offerta(bigint, varchar, text)`

> 👀 **Vedi anche**
>
> [vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali) ·
> [config.stati_doc_offerte_transizioni](/dbzero/config/tabelle/stati_doc_offerte_transizioni) ·
> [vendite.fn_annulla_offerta](/dbzero/vendite/funzioni/fn_annulla_offerta) ·
> [vendite.fn_offerta_proietta_stato_revisione](/dbzero/vendite/funzioni/fn_offerta_proietta_stato_revisione) ·
> guida [Il modello del documento di vendita](/guide/modello-documento-di-vendita) §5, §6

### 🎯 Scopo
(26-10-2026 — brief `brief-modello-documento-vendita` §13, giro dell'offerta)

**Il verbo di stato dell'offerta.** Ogni cambio di stato che un operatore chiede su un'offerta
passa da qui: l'emissione, l'accettazione, il rifiuto, l'annullo. Prima l'offerta non aveva un
verbo e lo stato lo scriveva il backend con un aggiornamento diretto.

### Regole

* **Il permesso** lo dice la riga del passaggio nella matrice: l'emissione e l'annullo di
  un'offerta accettata chiedono l'azione `emetti_offerta`; accettare, rifiutare e annullare una
  bozza chiedono solo il permesso sull'offerta. Senza l'azione: `E_PERMESSO_NEGATO`. Lo stato che
  l'offerta ha già: `E_DOC_GIA_NELLO_STATO`. Il superamento e il ritorno della revisione
  precedente sono passaggi del sistema e non si chiedono qui (`E_DOC_PASSAGGIO_DI_PROCESSO`).
* **La motivazione**: dove la riga del passaggio la chiede (il rifiuto e i due annulli) è
  obbligatoria, e una vuota o di soli spazi conta come assente
  (`E_OFFERTA_MOTIVAZIONE_OBBLIGATORIA`, campo `motivazione_rifiuto`). Quando c'è, si scrive
  sull'offerta prima dello stato, nella stessa operazione.
* **Le condizioni** del passaggio le giudica il guard di transizione dell'offerta: la matrice;
  all'emissione il listino da congelare, i prezzi autorizzati, gli indirizzi del cliente e le
  righe ammesse; all'accettazione i prezzi; all'annullo nessun contratto o ordine vivo nato
  dall'offerta.
* **L'annullo di una revisione** che fa tornare emessa la precedente non passa da qui senza
  conferma (`E_DOC_ANNULLO_CON_LEGAMI`): si conferma con
  [`vendite.fn_annulla_offerta`](/dbzero/vendite/funzioni/fn_annulla_offerta).
* **Il perimetro**: un'offerta che l'operatore non vede è come inesistente
  (`E_OFFERTA_NON_TROVATA`).
* Lo stato chiesto è il **codice** dello stato (`codice_interno`); uno stato che non c'è o è
  spento: `E_STATO_WORKFLOW_NON_TROVATO`.

### Chi la chiama

Il backend, per «Emetti», per l'esito (accetta, rifiuta) e per il cambio di stato; il verbo
d'annullo [`vendite.fn_annulla_offerta`](/dbzero/vendite/funzioni/fn_annulla_offerta), dopo la
conferma dei legami; la fixture dei test. Lo stato si scrive solo dai verbi dell'offerta: un
aggiornamento diretto della colonna è rifiutato (`E_DOC_STATO_SOLO_DAL_VERBO`).
