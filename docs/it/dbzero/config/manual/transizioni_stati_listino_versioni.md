## 📘 Documentazione Concettuale – Tabella `config.transizioni_stati_listino_versioni`

> 👀 **Vedi anche**
>
> [config.stati_doc_listino_versioni](/dbzero/config/tabelle/stati_doc_listino_versioni) ·
> [vendite.trgfn_listini_versioni_guard_transizione_stato](/dbzero/vendite/funzioni/trgfn_listini_versioni_guard_transizione_stato) ·
> [Il modello del documento di vendita](/guide/modello-documento-di-vendita)

### 🎯 Scopo
(28-10-2026 — brief `brief-modello-documento-vendita` §16, L-2 e L-3)

**I passaggi di stato di una versione di listino**: una riga attiva = un passaggio ammesso.
La giudica il guard di transizione a ogni cambio di stato; la legge il verbo comune
(`script.fn_doc_passaggio`).

| Da | A | Manuale | Azione | Chi lo scrive |
| --- | --- | --- | --- | --- |
| BOZZA | ATTIVA | sì | `attiva_listino` | [vendite.fn_attiva_versione_listino](/dbzero/vendite/funzioni/fn_attiva_versione_listino) |
| ATTIVA | CHIUSA | no (di processo: la causa è la data) | — | [vendite.fn_chiudi_versioni_listino_scadute](/dbzero/vendite/funzioni/fn_chiudi_versioni_listino_scadute), dal job |

### Regole

* `meta.manuale` è dichiarato su ogni riga (CHECK); `azione_processo_codename` è l'azione che
  il passaggio chiede, FK al catalogo `config.azioni_processo`.
* Una bozza non si chiude: si elimina. Una versione attiva non torna in bozza.
* Seed dal CSV `80_data/sql/config/transizioni_stati_listino_versioni.csv`.

---

{% include-markdown "signature-core.md" %}
