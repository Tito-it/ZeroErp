## 📘 Documentazione Concettuale – Vista `vendite.vw_preventivi_righe_smistabili_ordine`

> **Ultimo aggiornamento**: 3 novembre 2026

> 👀 **Vedi anche**
>
[vw_preventivi_righe_smistabili_commessa](vw_preventivi_righe_smistabili_commessa.md) (gemella, ramo servizi)
> [vendite.fn_preventivo_ha_residuo_ordine](/dbzero/vendite/funzioni/fn_preventivo_ha_residuo_ordine)
> [vendite.fn_push_preventivo_a_ordine](/dbzero/vendite/funzioni/fn_push_preventivo_a_ordine)

---
### 🎯 Scopo Principale

Vista **predicato unico** del ramo ordine: le righe preventivo **eleggibili**
allo smistamento merce→ordine. Capability (`fn_preventivo_ha_residuo_ordine`),
push (`fn_push_preventivo_a_ordine`) e Pannello Smistamento leggono da qui la
stessa verita' (brief-preventivi-ordini.md D8).

---

### Predicato di riga

Una riga e' eleggibile se:

* attiva (`COALESCE(attivo, true) IS TRUE`);
* natura di riga merce, cioè
  [script.fn_natura_e_merce](/dbzero/script/funzioni/fn_natura_e_merce)`(natura_vendita_id) IS TRUE`
  (destinazione `ORDINE_VENDITA`). Le righe a natura NULL, che il modello tratta
  come COMMESSA/pregresso, restano fuori: il building block dà NULL e `IS TRUE`
  le scarta;
* non gia' allocata a un ordine (`NOT EXISTS` su
  `ordini_righe.preventivo_riga_id`) — idempotenza di riga, garantita anche
  dal vincolo UNIQUE.

---

### Note operative

* `security_invoker = on` (policy RLS).
* I servizi (`COMMESSA`) sono esclusi: il loro predicato e'
  `vw_preventivi_righe_smistabili_commessa`.

### 🔄 rev 2026-09-13 — porta anche la data richiesta dal cliente

Colonna in coda: `data_consegna_richiesta_cliente` (`20260913-16`). È da questa
vista che `fn_push_preventivo_a_ordine` copia le righe, con un elenco esplicito
di colonne: senza, la data che il cliente ha chiesto sul preventivo si perdeva
nel passaggio all'ordine. Un secondo lettore delle righe dentro la funzione
sarebbe stato una seconda sede dello stesso predicato — che questa vista esiste
per evitare. Brief: `brief-db-modifiche-certe-ciclo-vendita-e-articolo`,
sezione 5.2.

### 🔄 rev 2026-11-03 — «è merce» dal building block

Il filtro merce era il JOIN con `config.nature_vendita` e la destinazione scritta
qui; ora è `script.fn_natura_e_merce`, la sede unica del predicato (regola del 2,
`20261103-19`). Stesse righe di prima, provato in transazione annullata. Brief:
`brief-db-addebito-trasporto-ordine` §8.1.
