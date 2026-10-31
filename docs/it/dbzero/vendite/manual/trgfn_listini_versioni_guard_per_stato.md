## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_listini_versioni_guard_per_stato()`

> **Ultimo aggiornamento**: 29 ottobre 2026

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
| ATTIVA | solo `valido_al`, e solo dai due verbi che la scrivono: «Chiudi» (la chiusura programmata) e l'attivazione di una nuova (chiude le precedenti) | no |
| CHIUSA | niente | no |

### Regole

* Un campo cambiato fuori da quelli ammessi: `E_LISTINO_VERSIONE_CAMPO_NON_MODIFICABILE`, col
  primo campo nell'ordine delle colonne.
* La fine di una versione attiva cambiata da una modifica diretta, fuori da
  [«Chiudi»](/dbzero/vendite/funzioni/fn_programma_chiusura_versione_listino) e
  dall'[attivazione](/dbzero/vendite/funzioni/fn_attiva_versione_listino):
  `E_LISTINO_VERSIONE_FINE_SOLO_DAL_VERBO` (dal 29-10-2026, §16.15). Così la regola «la fine non
  sta nel passato» di «Chiudi» non si aggira. I due verbi aprono una «porta» per la versione che
  scrivono, che vale solo se chi scrive è il proprietario della tabella: l'applicazione da sola
  non la apre.
* Se una versione si elimina lo dice
  [script.fn_check_versione_listino_eliminabile](/dbzero/script/funzioni/fn_check_versione_listino_eliminabile),
  la stessa regola del verbo [vendite.fn_elimina_versione_listino](/dbzero/vendite/funzioni/fn_elimina_versione_listino)
  e del pulsante «Elimina»; il guard ne solleva il primo motivo:
  * fuori dalla BOZZA, `E_LISTINO_VERSIONE_NON_ELIMINABILE`: una versione attiva o chiusa è stata
    usata per i prezzi;
  * una BOZZA che un documento usa (un contratto, un'offerta, un'attività di commessa),
    `E_LISTINO_VERSIONE_CITATA` (dal 28-10-2026, §16.11).
* Lo stato non è un campo di questa regola: i suoi passaggi li giudica il guard di transizione,
  e lo scrive solo un verbo. Le colonne d'audit e la generata `validita` non contano.

---

{% include-markdown "signature-core.md" %}
