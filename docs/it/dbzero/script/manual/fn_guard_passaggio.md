## 📘 Documentazione Concettuale – Funzione `script.fn_guard_passaggio`

> 👀 **Vedi anche**
>
> [script.fn_doc_passaggio](/dbzero/script/funzioni/fn_doc_passaggio) ·
> [script.fn_doc_scrivi_stato](/dbzero/script/funzioni/fn_doc_scrivi_stato) ·
> [script.fn_guard_azione](/dbzero/script/funzioni/fn_guard_azione) ·
> guida [Il modello del documento di vendita](/guide/modello-documento-di-vendita) §5-§6

### 🎯 Scopo
(25-10-2026 — brief `brief-modello-documento-vendita` §7, decisioni M-1, M-3, M-4, S-2;
rivisto il 26-10-2026, §9.10: lo stato che il documento ha già)

**La prima riga del verbo di stato.** Ogni cambio di stato di un documento sul
modello passa da un verbo, e il verbo comune ha due metà:

1. questa: il **permesso** del passaggio, prima di scrivere qualunque cosa;
2. [`script.fn_doc_scrivi_stato`](/dbzero/script/funzioni/fn_doc_scrivi_stato): la
   **scrittura** dello stato attraverso la porta.

Le metà sono due perché i verbi dei documenti lavorano **fra** l'una e l'altra:
la bolla scrive i prelievi dopo il permesso e prima dello stato, e i movimenti
dopo; il reso i rientri, la proiezione dell'ordine, i carichi.

| La riga del passaggio | Che cosa fa |
| --- | --- |
| non c'è, e lo stato chiesto è quello che il documento ha già | `E_DOC_GIA_NELLO_STATO`, prima di ogni lavoro del verbo |
| non c'è, per un cambio di stato | passa: il passaggio lo rifiuta il guard di transizione all'`UPDATE` (la matrice ha un giudice solo) |
| è di processo (`manuale = false`) | `E_DOC_PASSAGGIO_DI_PROCESSO`: lo scrive solo il verbo che ne è la causa |
| chiede un'azione | `script.fn_guard_azione`: senza l'azione, `E_PERMESSO_NEGATO` |
| non chiede un'azione | passa: basta il permesso sul documento, che controlla il backend |

### Regole

* **Lo stato che il documento ha già si rifiuta qui, non nel guard di transizione.** Il
  guard giudica i **cambi** di stato: quando lo stato non cambia esce subito, e deve farlo,
  perché un `UPDATE` che riscrive lo stesso stato (il salvataggio della riga intera) è
  lecito. Una richiesta al verbo che non cambia niente (un secondo «Emetti», la stessa
  conferma inviata due volte) la vede solo il verbo: per questo la regola sta nella sua
  prima riga, comune a tutti i documenti, e parla prima dei controlli del verbo (sulla
  bolla, quelli della merce). Una riga X → X nella matrice, se ci fosse, sarebbe un
  passaggio come gli altri.
* ⛔ Nessun controllo del **livello** sul documento qui: lo fa l'endpoint, come per
  gli altri verbi del dominio (l'operatore dei pgTAP è bloccato su più aree, e un
  `fn_guard_livello` nel verbo romperebbe ogni fixture che lo attraversa).
* Uso: dopo aver preso la testata `FOR UPDATE`,
  `PERFORM script.fn_guard_passaggio(v_utente, 'vendite.ddt', v_ddt.stato_doc_ddt_id, v_stato_a_id)`.
* Consumatori: `vendite.fn_cambia_stato_ddt`, `vendite.fn_cambia_stato_preventivo`,
  `vendite.fn_cambia_stato_ordine`, `vendite.fn_conferma_reso`, `vendite.fn_annulla_reso`.
