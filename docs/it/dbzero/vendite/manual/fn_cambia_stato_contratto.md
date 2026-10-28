## 📘 Documentazione Concettuale – Funzione `vendite.fn_cambia_stato_contratto(bigint, varchar)`

> 👀 **Vedi anche**
>
> [vendite.contratti](/dbzero/vendite/tabelle/contratti) ·
> [config.transizioni_stati_contratti](/dbzero/config/tabelle/transizioni_stati_contratti) ·
> [vendite.fn_cessa_contratto](/dbzero/vendite/funzioni/fn_cessa_contratto) ·
> [vendite.fn_annulla_contratto](/dbzero/vendite/funzioni/fn_annulla_contratto) ·
> guida [Il modello del documento di vendita](/guide/modello-documento-di-vendita) §5, §6

### 🎯 Scopo
(26-10-2026 — brief `brief-modello-documento-vendita` §11, giro del contratto)

**Il verbo di stato del contratto.** Ogni cambio di stato che un operatore chiede su un
contratto passa da qui: l'attivazione (che è l'emissione del contratto) e l'annullo della
bozza. Prima il contratto non aveva un verbo e lo stato lo scriveva il backend con un
aggiornamento diretto.

### Regole

* **Il permesso** lo dice la riga del passaggio nella matrice: l'attivazione e la
  cessazione chiedono l'azione `emetti_contratto`; l'annullo di una bozza chiede solo il
  permesso sul documento. Senza l'azione: `E_PERMESSO_NEGATO`. Lo stato che il contratto
  ha già: `E_DOC_GIA_NELLO_STATO`.
* **Le condizioni** del passaggio le giudica il guard di transizione del contratto: la
  matrice, all'attivazione prezzi autorizzati, indirizzi del cliente, righe ammesse e
  nessun contratto vincolante sovrapposto; alla cessazione una data di fine **arrivata**.
* **La cessazione con la sua data non passa da qui** ma da
  [`vendite.fn_cessa_contratto`](/dbzero/vendite/funzioni/fn_cessa_contratto), che decide
  fra cessazione di oggi e programmata. Chiesta qui, la cessazione passa solo se la data
  di fine c'è già ed è arrivata.
* **Il perimetro**: un contratto che l'operatore non vede è come inesistente
  (`E_CONTRATTO_NON_TROVATO`).
* Lo stato chiesto è il **codice** dello stato (`codice_interno`); uno stato che non c'è
  o è spento: `E_STATO_WORKFLOW_NON_TROVATO`.

### Chi la chiama

Il backend, per «Emetti»; il verbo d'annullo
[`vendite.fn_annulla_contratto`](/dbzero/vendite/funzioni/fn_annulla_contratto), dopo aver
ritirato i legami; la fixture dei test. Lo stato si scrive solo dai verbi del contratto:
un aggiornamento diretto della colonna è rifiutato (`E_DOC_STATO_SOLO_DAL_VERBO`).
