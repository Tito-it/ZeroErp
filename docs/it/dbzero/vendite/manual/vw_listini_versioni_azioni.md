## 📘 Documentazione Concettuale – Vista `vendite.vw_listini_versioni_azioni`

> **Ultimo aggiornamento**: 29 ottobre 2026

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

### Regole

* Il motivo è il **primo** della `fn_check` dell'azione
  ([attivabile](/dbzero/script/funzioni/fn_check_versione_listino_attivabile),
  [eliminabile](/dbzero/script/funzioni/fn_check_versione_listino_eliminabile),
  [chiudibile](/dbzero/script/funzioni/fn_check_versione_listino_chiudibile)): è quello con cui
  il verbo e il guard rifiutano.
* «Chiudi» si legge senza data: la fine nel passato la giudica il verbo con la data scelta nel
  dialogo.
* Lo stato non c'è: chi può attivare da quale stato lo dice la riga lista
  (`script.fn_doc_azioni_permesse`).
* `security_invoker`: i soli listini del proprio perimetro. Si filtra per `listino_id`.

---

{% include-markdown "signature-core.md" %}
