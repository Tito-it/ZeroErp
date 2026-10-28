## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_listino`

> 👀 **Vedi anche**
>
> • [dbops.fn_pgtap_crea_cliente_ba](/dbzero/dbops/funzioni/fn_pgtap_crea_cliente_ba) — il cliente la cui utility dà il listino
>
> • [vendite.listini](/dbzero/vendite/tabelle/listini), [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni) — le due tabelle che scrive
>
Guide: [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) · brief `brief-db-fixture-che-costruiscono-giro-2` (§11)

---
### 🎯 Scopo Principale

(rev 2026-09-23 — D7, lotto 2)

**Un listino con una versione ATTIVA**, dell'azienda di chi agisce, per l'utility scelta dal
test. ⭐ Rev 2026-10-28: la versione nasce in bozza, prende **una riga d'appoggio** (un articolo
suo, codice `PGTAP_LST_ART_<casuale>`) e si attiva dal verbo, via `dbops.fn_pgtap_porta_a_stato`:
una versione si attiva solo con un prezzo. Chi conta le righe della versione ne trova una in più. `vendite.listini` è anagrafica: su un database ricostruito è vuota, e «il primo listino
attivo» non esiste.

```sql
-- un listino in vigore da oggi, senza scadenza
CREATE TEMP TABLE tmp_listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino(<utility_id>, 'offerta');

-- una versione già scaduta, per chi collauda la chiusura
SELECT * FROM dbops.fn_pgtap_crea_listino(<utility_id>, 'chiusura',
                                          DATE '2022-01-01', DATE '2022-12-31');
```

Restituisce `listino_id`, `listino_versione_id` e la `tipologia_id` scelta.

---
### 🧭 Le due cose che non si scelgono

* **L'emittente è quello di chi agisce.** Il listino ha un controllo di perimetro: un
  emittente fuori dall'azienda dell'operatore viene rifiutato. Quindi il contesto va aperto
  **prima** di chiamare la funzione, e senza contesto la funzione si ferma con un messaggio
  che lo dice.
* **La tipologia è la prima ammessa per l'utility.** Non tutte le tipologie valgono per
  tutte le utility (`config.listini_tipologie_utilities`): la prima per id, per esempio, non
  vale per l'utility BASE, che ammette solo prodotti e servizi.

---
### 🚫 Cosa NON scrive

Le **righe** del listino (prezzi, componenti) e le versioni in stati diversi da ATTIVA: sono
il caso del test.
