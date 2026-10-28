## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_listini_versioni_guard_per_stato()`

> 👀 **Vedi anche**
>
> [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni) ·
> [vendite.trgfn_listini_versioni_guard_transizione_stato](/dbzero/vendite/funzioni/trgfn_listini_versioni_guard_transizione_stato)

### 🎯 Scopo
(28-10-2026 — brief `brief-modello-documento-vendita` §16, L-5)

**Che cosa si cambia di una versione di listino, stato per stato**, e quando si elimina.
Montato da `trg_listini_versioni_a10_guard_per_stato_upd` (BEFORE UPDATE) e
`trg_listini_versioni_a10_guard_per_stato_dlt` (BEFORE DELETE).

| Stato | Si cambia | Si elimina |
| --- | --- | --- |
| BOZZA | tutto | sì |
| ATTIVA | solo `valido_al` (la chiusura programmata; anche quella delle precedenti all'attivazione di una nuova) | no |
| CHIUSA | niente | no |

### Regole

* Un campo cambiato fuori da quelli ammessi: `E_LISTINO_VERSIONE_CAMPO_NON_MODIFICABILE`, col
  primo campo nell'ordine delle colonne.
* Un'eliminazione fuori dalla BOZZA: `E_LISTINO_VERSIONE_NON_ELIMINABILE`. Una versione attiva o
  chiusa è stata usata per i prezzi.
* Lo stato non è un campo di questa regola: i suoi passaggi li giudica il guard di transizione,
  e lo scrive solo un verbo. Le colonne d'audit e la generata `validita` non contano.

---

{% include-markdown "signature-core.md" %}
