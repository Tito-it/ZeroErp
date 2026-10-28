## 📘 Documentazione Concettuale – Vista `vendite.vw_listini_versioni_azioni`

> 👀 **Vedi anche**
>
> [config.azioni_riga](/dbzero/config/tabelle/azioni_riga) ·
> [script.fn_check_versione_listino_attivabile](/dbzero/script/funzioni/fn_check_versione_listino_attivabile) ·
> [vendite.fn_attiva_versione_listino](/dbzero/vendite/funzioni/fn_attiva_versione_listino)

### 🎯 Scopo
(28-10-2026 — brief `brief-modello-documento-vendita` §16, L-4)

**L'azione di riga «Attiva» delle versioni di listino.** Per ogni versione dice se qualcosa ne
vieta l'attivazione e perché. È la superficie dell'azione `ATTIVA_VERSIONE_LISTINO` nel registro
[`config.azioni_riga`](/dbzero/config/tabelle/azioni_riga).

| Colonna | Cosa dice |
| --- | --- |
| `versione_id`, `listino_id` | la versione |
| `attivazione_blocco_reason` | il motivo per cui «Attiva» è spento; `NULL` = niente lo vieta |
| `attivazione_blocco_reason_key` | la chiave di traduzione dello stesso motivo |

### Regole

* Il motivo è il **primo** della `fn_check`: è quello con cui il verbo e il guard rifiutano.
* Lo stato non c'è: chi può attivare da quale stato lo dice la riga lista
  (`script.fn_doc_azioni_permesse`).
* `security_invoker`: i soli listini del proprio perimetro. Si filtra per `listino_id`.

---

{% include-markdown "signature-core.md" %}
