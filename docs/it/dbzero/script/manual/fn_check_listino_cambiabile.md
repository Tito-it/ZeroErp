## 📘 Documentazione Concettuale – Funzione `script.fn_check_listino_cambiabile()`

> 👀 **Vedi anche**
>
> • [script.trgfn_doc_guard_listino_con_righe](/dbzero/script/funzioni/trgfn_doc_guard_listino_con_righe) — il guard che solleva il primo motivo
> • [script.fn_check_listino_documento](/dbzero/script/funzioni/fn_check_listino_documento) — l'altra regola sul listino: utility ed emittente

---

### 🎯 Scopo Principale

(nata il 2026-10-11, brief `brief-db-testata-dopo-emissione`, §11, R-DB-4 e D-11 di Tid)

Dice **perché** il listino di un contratto o di un'offerta non può cambiare. Risponde con un
elenco di motivi: vuoto vuol dire che il cambio è ammesso. Non solleva errori: lo fa il guard
che la chiama.

| Motivo | Quando | Codice |
| --- | --- | --- |
| `LISTINO_CON_RIGHE` | si mette o si sostituisce il listino, e il documento ha righe attive | `E_DOC_LISTINO_CAMBIO_CON_RIGHE` |
| `LISTINO_RIMOZIONE_CON_ECCEZIONI` | si toglie il listino, e restano eccezioni di prezzo (OVERRIDE) o di esclusione | `E_DOC_LISTINO_RIMOZIONE_CON_ECCEZIONI` |

Il perché sta nel modello: le righe del documento sono state scelte contro il listino di
prima. Le aggiunte di articoli fuori listino valgono anche senza listino, e non fermano la
rimozione.

Le due regole vivevano solo nel backend del contratto. Per decisione di Tid (D-11) valgono
anche per l'offerta, che ha le stesse righe. Fuori bozza il listino è già fermo dal lock di
testata: queste regole contano in bozza.
