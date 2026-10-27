## 📘 Documentazione Concettuale – Funzione `vendite.fn_cambia_stato_commessa(bigint, varchar)`

> 👀 **Vedi anche**
>
> [vendite.commesse](/dbzero/vendite/tabelle/commesse) ·
> [vendite.transizioni_stati_commessa](/dbzero/vendite/tabelle/transizioni_stati_commessa) ·
> [vendite.fn_annulla_commessa](/dbzero/vendite/funzioni/fn_annulla_commessa) ·
> [vendite.fn_commessa_proietta_stato_emittibile](/dbzero/vendite/funzioni/fn_commessa_proietta_stato_emittibile) ·
> guida [Il modello del documento di vendita](/guide/modello-documento-di-vendita) §5, §6

### 🎯 Scopo
(rev 2026-06-07; ultima revisione 2026-10-26 — brief `brief-modello-documento-vendita` §14, giro della commessa)

**Il verbo di stato della commessa.** Ogni cambio di stato che un operatore chiede su una
commessa passa da qui: «rendi pronta», «riapri», «chiudi», l'annullo della bozza. Dal 2026-10-26
è sul verbo comune del modello; prima era un aggiornamento diretto senza controllo del permesso,
con un terzo parametro `p_user` che non c'è più (chi scrive lo dice l'audit dalla sessione).

### Regole

* **Il permesso** lo dice la riga del passaggio nella matrice: «rendi pronta», «riapri», «chiudi»
  e l'annullo di una commessa non in bozza chiedono l'azione `cambia_stato_commessa`; l'annullo
  della bozza chiede solo il permesso sulla commessa. Senza l'azione: `E_PERMESSO_NEGATO`.
* **Lo stato che la commessa ha già**: `E_DOC_GIA_NELLO_STATO`. Un **passaggio di processo**
  chiesto a mano: `E_DOC_PASSAGGIO_DI_PROCESSO`.
* **Le condizioni** del passaggio le giudica il guard di transizione: la matrice
  (`E_COMMESSA_STATO_TRANSIZIONE_INVALIDA`), le righe approvate per «rendi pronta», la commessa
  chiudibile e annullabile.
* **L'annullo con legami** non passa da qui senza conferma: si conferma con
  [`vendite.fn_annulla_commessa`](/dbzero/vendite/funzioni/fn_annulla_commessa).
* **Il perimetro**: una commessa che l'operatore non vede è come inesistente
  (`E_COMMESSA_NON_TROVATA`).
* Lo stato chiesto è il **codice** dello stato (`codice_interno`); uno stato che non c'è o è
  spento (IN_ESECUZIONE, ritirato): `E_STATO_WORKFLOW_NON_TROVATO`.

Ritorna `commessa_id`, `stato_da`, `stato_a`.

### Chi la chiama

Il backend, per le azioni di stato della commessa; il verbo d'annullo, dopo la conferma dei
legami; la fixture dei test. Il passaggio a pronta che segue un invio della push non passa da
qui: lo scrive [`vendite.fn_commessa_proietta_stato_emittibile`](/dbzero/vendite/funzioni/fn_commessa_proietta_stato_emittibile),
col permesso della push. Un aggiornamento diretto della colonna di stato è rifiutato
(`E_DOC_STATO_SOLO_DAL_VERBO`).

---

{% include-markdown "signature-core.md" %}
