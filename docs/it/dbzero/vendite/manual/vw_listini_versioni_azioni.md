## 📘 Documentazione Concettuale – Vista `vendite.vw_listini_versioni_azioni`

> **Ultimo aggiornamento**: 15 novembre 2026

> 👀 **Vedi anche**
>
> [config.azioni_riga](/dbzero/config/tabelle/azioni_riga) ·
> [script.fn_check_versione_listino_attivabile](/dbzero/script/funzioni/fn_check_versione_listino_attivabile) ·
> [vendite.fn_attiva_versione_listino](/dbzero/vendite/funzioni/fn_attiva_versione_listino) ·
> [vendite.fn_programma_chiusura_versione_listino](/dbzero/vendite/funzioni/fn_programma_chiusura_versione_listino)

### 🎯 Scopo
(28-10-2026 — brief `brief-modello-documento-vendita` §16, L-4)

**Le azioni di riga «Attiva», «Elimina» e «Chiudi» delle versioni di listino.** Per ogni versione
dice se qualcosa ne vieta l'attivazione, l'eliminazione o la chiusura, e perché. È la superficie
delle azioni `ATTIVA_VERSIONE_LISTINO`, `ELIMINA_VERSIONE_LISTINO` (dal 28-10-2026, §16.11) e
`CHIUDI_VERSIONE_LISTINO` (dal 29-10-2026, §16.14) nel registro
[`config.azioni_riga`](/dbzero/config/tabelle/azioni_riga). «Clona» non ha colonne: si copia da
qualunque stato.

| Colonna | Cosa dice |
| --- | --- |
| `versione_id`, `listino_id` | la versione |
| `attivazione_blocco_reason` | il motivo per cui «Attiva» è spento; `NULL` = niente lo vieta |
| `attivazione_blocco_reason_key` | la chiave di traduzione dello stesso motivo |
| `eliminazione_blocco_reason` | il motivo per cui «Elimina» è spento (non in bozza, usata da un documento); `NULL` = si elimina |
| `eliminazione_blocco_reason_key` | la chiave di traduzione dello stesso motivo |
| `chiusura_blocco_reason` | il motivo per cui «Chiudi» è spento (la versione non è attiva); `NULL` = si chiude |
| `chiusura_blocco_reason_key` | la chiave di traduzione dello stesso motivo |
| `aggiunta_riga_blocco_reason` | il motivo per cui «Aggiungi riga» è spento: `VERSIONE_CHIUSA` o `VERSIONE_NON_IN_BOZZA`, il primo motivo di `script.fn_check_listino_riga_scrivibile` senza riga, lo stesso che il guard di stato delle righe solleva sull'INSERT; `NULL` = la riga si aggiunge (la versione è in bozza) |
| `aggiunta_riga_blocco_reason_key` | la chiave di traduzione dello stesso motivo |
| `variazione_blocco_reason` / `_key` | «Variazione %» dei prezzi delle righe: lo stesso motivo, sollevato dal verbo [`vendite.fn_varia_prezzi_versione_listino`](/dbzero/vendite/manual/fn_varia_prezzi_versione_listino) per la versione, anche nell'anteprima e anche quando il gesto non prende righe |
| `prezzi_bundle_blocco_reason` / `_key` | i prezzi dei componenti di un kit (il dialog bundle): lo stesso motivo, sollevato dal guard di `vendite.listini_righe_componenti` |
| `periodicita_kit_blocco_reason` / `_key` | la periodicità di un kit (`vendite.listini_kit`): lo stesso motivo, sollevato dal guard del kit |

### Regole

* Il motivo è il **primo** della `fn_check` dell'azione
  ([attivabile](/dbzero/script/funzioni/fn_check_versione_listino_attivabile),
  [eliminabile](/dbzero/script/funzioni/fn_check_versione_listino_eliminabile),
  [chiudibile](/dbzero/script/funzioni/fn_check_versione_listino_chiudibile)): è quello con cui
  il verbo e il guard rifiutano.
* **Le scritture della versione si fanno solo in bozza**: aggiunta di righe, variazione, prezzi dei
  componenti e periodicità dei kit hanno quattro coppie di colonne (un'azione, le sue colonne) e
  una regola sola, `script.fn_check_listino_riga_scrivibile`, calcolata una volta. Il prezzo
  sbagliato di una riga in uso si **rettifica**: la superficie è
  [`vendite.vw_listini_righe_azioni`](/dbzero/vendite/manual/vw_listini_righe_azioni).
* «Chiudi» si legge senza data: la fine nel passato la giudica il verbo con la data scelta nel
  dialogo.
* Lo stato non c'è: chi può attivare da quale stato lo dice la riga lista
  (`script.fn_doc_azioni_permesse`).
* `security_invoker`: i soli listini del proprio perimetro. Si filtra per `listino_id`.

---

{% include-markdown "signature-core.md" %}
