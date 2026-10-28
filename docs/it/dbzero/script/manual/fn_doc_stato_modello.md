## 📘 Documentazione Concettuale – Funzione `script.fn_doc_stato_modello(regclass)`

> 👀 **Vedi anche**
>
> [script.fn_doc_passaggio](/dbzero/script/funzioni/fn_doc_passaggio) ·
> [script.fn_doc_scrivi_stato](/dbzero/script/funzioni/fn_doc_scrivi_stato) ·
> [script.trgfn_doc_stato_solo_dal_verbo](/dbzero/script/funzioni/trgfn_doc_stato_solo_dal_verbo) ·
> guida [Il modello del documento di vendita](/guide/modello-documento-di-vendita)

### 🎯 Scopo
(25-10-2026 — brief `brief-modello-documento-vendita` §7)

**La mappa dei documenti.** Per una testata dice dove sta il suo stato e quale
tabella ne elenca i passaggi ammessi:

| Colonna | Che cosa |
| --- | --- |
| `colonna_stato` | la colonna della testata che porta lo stato |
| `vocabolario` | la tabella degli stati |
| `matrice` | la tabella dei passaggi |
| `colonna_da`, `colonna_a`, `colonna_vivo` | i nomi delle colonne della matrice (la fattura ne ha di diversi) |
| `filtro` | la condizione in più della fattura e del lotto, che condividono la stessa matrice |

Nessuna riga: la tabella non è un documento con una matrice.

### Regole

* È **codice, non configurazione**: una testata nuova entra con un changeSet che
  riscrive la funzione.
* La leggono il verbo comune (`fn_doc_passaggio`, `fn_doc_scrivi_stato`), la porta
  e la fixture `dbops.fn_pgtap_porta_a_stato`. Prima la mappa stava solo dentro la
  fixture: alla seconda occorrenza è diventata un building block, e la copia si è
  ritirata.
