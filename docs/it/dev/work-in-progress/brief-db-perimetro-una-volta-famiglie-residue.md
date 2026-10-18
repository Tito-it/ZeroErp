# Brief DB — Il perimetro una volta per istruzione: le famiglie che restano

## ⏭️ Chi riparte — aggiornato al 2026-10-18

**Riparte: Tid**, con le decisioni P-1…P-3. Aperto, **non iniziato**.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | Tid | decidere P-1 (perimetro e ordine delle famiglie), P-2 (la forma per le famiglie del cliente), P-3 (`via_coppia`) | §4 | — |
| 2 | sessione DB | per famiglia: forma, changeSet, presidio, prove come nel brief d'origine | §3 | 1 |

Decisioni aperte di Tid: P-1, P-2, P-3. Niente da committare.

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-10-18. **A chi:** Tid.
> **Origine:** il debito residuo di
> [brief-db-plancache-funzioni-con-query-incorporate](../work-done/brief-db-plancache-funzioni-con-query-incorporate.md)
> (D-3b-2, §5quinquies), archiviato il 2026-10-18. Voce nel registro: **D36** di
> [migliorie-generali-da-test-valutazione](migliorie-generali-da-test-valutazione.md).
> **Ricadute BE/FE:** nessuna prevista.

## 1. Il difetto, sul modello

Una policy che chiede «chi guarda vede questa riga?» calcola una parte della risposta che **non
dipende dalla riga**: il perimetro di chi guarda (super admin, veste, whitelist, il cliente o il
fornitore della sessione). Se lo calcola dentro la funzione chiamata per riga, lo ricalcola a ogni
riga letta: costo per costruzione **righe lette × catena**.

Il brief d'origine l'ha curato per tutta la famiglia dell'**operatore** (ef_whitelist): il perimetro
in una sottoquery scalare non correlata, valutata una volta per istruzione, e per riga solo
l'appartenenza (`script.fn_scope_ef_perimetro`, `script.fn_resolve_emittente_fiscale_id`;
linee-guida-sql §10.3). Restano le policy elencate al §2.

## 2. Che cosa resta (censimento, dbdev, 2026-10-18)

Fatto datato, `pg_policies` su 310 policy:

| Funzione di scope nelle policy | Policy | Schemi | Famiglia |
| --- | --- | --- | --- |
| `fn_scope_ba_ownership_via_fattura` | 10 | vendite | cliente portale |
| `fn_scope_ba_ownership` | 5 | anagrafiche, vendite | cliente portale |
| `fn_scope_ba_ownership_via_fattura_sdi` | 1 | vendite | cliente portale |
| `fn_scope_cliente_ownership` | 3 | shop, vendite | cliente |
| `fn_scope_cliente_ownership_via_ordine` | 3 | vendite | cliente |
| `fn_scope_cliente_ownership_via_ordine_riga` | 2 | vendite | cliente |
| `fn_scope_shop_via_ordine` | 3 | vendite | shop |
| `fn_scope_shop_via_ordine_riga` | 2 | vendite | shop |
| `fn_scope_shop_via_ba` | 1 | anagrafiche | shop |
| `fn_scope_fornitore_ownership` | 2 | acquisti | fornitore portale |
| `fn_scope_email_ambito` | 2 | config | email |
| `fn_scope_note_cliente` | 1 | vendite | note |
| `fn_scope_note_shop` | 1 | vendite | note |
| `fn_scope_note_ef_whitelist` | 1 | vendite | note, **operatore** |
| `fn_scope_note_magazzino_ef_whitelist` | 1 | magazzino | note, **operatore** |
| `fn_scope_ef_whitelist_via_coppia` | 1 | anagrafiche | **operatore** |

⚠️ Le tre righe «operatore» sono della famiglia già curata, ma restano per riga:

* `fn_scope_note_ef_whitelist` e `fn_scope_note_magazzino_ef_whitelist` non hanno il prefisso
  `via_*`, quindi il test 5 del presidio `script/test-scope-ef-perimetro-una-volta-per-istruzione-v1`
  **non le vede** (guarda gli adattatori `fn_scope_ef_whitelist_via_*`). Debito non dichiarato fino
  a oggi: dichiarato qui.
* `fn_scope_ef_whitelist_via_coppia` (`anagrafiche.istanze_dati_precontrattuali`): la chiave è una
  **coppia** di colonne (istanza, utility) e il risolutore prende un valore solo. È l'unico nome
  nell'elenco del debito del test 5.

## 3. La forma che c'è già

Dal brief d'origine, applicata e misurata: il perimetro in **una** sottoquery (due lo calcolano
due volte per istruzione e le letture di una riga pagano il doppio); l'emittente — qui: la cosa di
cui chiede la famiglia — risolto per riga da una funzione `SECURITY DEFINER` con una lettura per
chiave, senza rieseguire la policy del padre; presidio sul testo **e sul piano**. Ogni famiglia
porta una domanda sua (il cliente della riga, il billing account, l'ambito email), e prima di
scrivere va guardato se esiste già la funzione che risponde in forma di **insieme** (regola del 2:
per l'operatore c'era `script.fn_get_emittenti_scope_pk_ids`).

## 4. Decisioni attese

* **P-1** — il perimetro e l'ordine: le tre righe «operatore» per prime (stessa forma già pronta),
  poi le famiglie del cliente, o tutte insieme.
* **P-2** — per le famiglie del cliente, shop e fornitore: il difetto è lo stesso, per costruzione.
  La domanda è di sede, non di urgenza: curarle in questo brief, o dentro i cantieri che possiedono
  quei perimetri (shop, acquisti, portale cliente), che le stanno ridisegnando.
* **P-3** — `via_coppia`: un risolutore a due valori (o una colonna del billing account sulla
  tabella), o resta dichiarata.
