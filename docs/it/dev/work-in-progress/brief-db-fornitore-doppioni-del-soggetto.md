# Brief DB — i doppioni del soggetto sul fornitore

> **Chi scrive:** sessione BE/FE (`dev/backend-tid`), revisione `/verifica` del 2026-11-21. **A chi:** team DB
> (`dev/db-tid`); Tid per le decisioni aperte.

## ⏭️ Chi riparte

**Riparte: il team DB** col giro A del §3. Il lato BE/FE è fatto (§1), da committare (Tid). Decisioni di Tid: prese
il 2026-11-21 (§2).

| # | Chi | Che cosa | Dipende da |
| --- | --- | --- | --- |
| 1 | ✅ team BE/FE | Form, dettaglio, PATCH e creazione del fornitore senza i sei campi (2026-11-21) | — |
| 2 | ✅ Tid | D-1 «a», D-2 «non serve» (2026-11-21) | — |
| 3 | **team DB** ⏭️ | Giro A: via le tre colonne dal catalogo della lista (§3) | 2 |
| 4 | team BE | Via le tre colonne dalla SELECT della lista (§4) | 3 |
| 5 | team DB | Giro B: via i sei campi da tabella, vista, madre e guard (§3) | 4 |
| 6 | team DB | Chiusura: archiviazione | 5 |

## 1. Che cosa ha fatto il BE/FE (2026-11-21)

`anagrafiche.fornitori` porta sei campi che hanno la loro sede altrove, o nessuna:

| Campo | Sede |
| --- | --- |
| `giorni_pagamento`, `fine_mese` | il termine (`config.termini_pagamento`, via `termine_pagamento_id`) |
| `split_payment` | il soggetto (`anagrafiche.soggetti.split_payment`, `character(1)`) |
| `canale_fe`, `pec_email` | i dati societari del soggetto (`anagrafiche.dati_societari`) |
| `bollo_esente` | **nessuna**, e sul fornitore non serve (D-2) |

Sono usciti da: il form di `FornitoreDrawer.vue`; il dettaglio (`FornitoriRepository.get_fornitore`); la whitelist
della PATCH (`FORNITORE_UPDATE_ALLOWED`: un PATCH che li porta ora è un 400, test
`test_update_fornitore_campi_del_soggetto_sono_400`); i campi della creazione
(`FornitoriService._extract_fornitore_data`); lo schema OpenAPI delle due view; la lettura del fornitore del portale
(`PortaleRepository`, `pec_email`, senza lettori). Come sul cliente, che non li ha.

**Restano, e sono il motivo di questo brief:**

* la **lista** `anagrafiche.fornitori` mostra ancora tre colonne di `ui.lista_colonna` (codici `pec_email`,
  `canale_fe`, `split_payment`), lette da `vw_fornitori_dettaglio`, cioè da `f.*`. Mostrano il valore **del
  fornitore**, che nessuno può più modificare, e non quello del soggetto: il dato a video diverge in silenzio dal
  dato vero. Il BE le tiene nella SELECT di `list_fornitori` solo perché il catalogo le espone;
* le **colonne** della tabella, la vista, l'allowlist di `anagrafiche.fn_crea_fornitore` (`p_campi` accetta ancora le
  sei chiavi) e `trgfn_fornitori_guard_normalize` (normalizza `canale_fe`).

## 2. Decisioni di Tid (2026-11-21)

* **D-1 — le tre colonne della lista. ✅ Decisa: «a», si ritirano.** (a) si ritirano dal catalogo; (b) si rifanno dalla sede vera (split payment
  dal soggetto, canale e PEC da `dati_societari`), come colonne nuove. **Raccomandata (a)**: né `clienti` né
  `billing_account` portano questi campi, e la lista clienti non ha colonne equivalenti (verificato su
  `lista_colonna.csv` il 2026-11-21); se servono su tutte e due le liste, è uno sviluppo delle colonne di soggetto,
  simmetrico. Una colonna che legge il doppione è peggio di nessuna colonna.
* **D-2 — `bollo_esente`. ✅ Decisa: non serve sul fornitore, si ritira con gli altri cinque.** A differenza degli altri cinque non ha un'altra sede (sta solo su `emittenti_fiscali` e
  sulle fatture): il form l'ha tolto per simmetria col cliente, che non lo ha. Da confermare che sul fornitore non
  serve (il bollo della fattura passiva lo porta il documento del fornitore); se serve, torna nel form e non si
  ritira.

## 3. Richiesta al team DB

**Giro A — il catalogo (prima del BE).**

1. `ui.lista_colonna`, lista `anagrafiche.fornitori`: via le colonne di codice `pec_email`, `canale_fe`,
   `split_payment` (D-1 «a»), con le loro tracce nelle preferenze e nei preset della lista, se ne hanno.

**Giro B — i campi (dopo il passo 4, il BE).**

2. `anagrafiche.fornitori`: via `giorni_pagamento`, `fine_mese`, `split_payment`, `bollo_esente`, `canale_fe`,
   `pec_email`, coi loro CHECK (`char_length(canale_fe) = 7`) e la normalizzazione di `canale_fe` in
   `trgfn_fornitori_guard_normalize`.
3. `vw_fornitori_dettaglio`: via le stesse sei colonne.
4. `anagrafiche.fn_crea_fornitore`: via le sei chiavi dall'allowlist di `p_campi` (diventano `E_CAMPO_NON_AMMESSO`)
   e dal `COMMENT`.
5. Manuale `docs/it/dbzero/anagrafiche/manual/fornitori.md`: le righe dei campi e il consiglio «compila uno tra
   `canale_fe` e `pec_email`».

**Chi cambia per primo, e perché in due giri.** Il BE ha già smesso di scrivere e leggere i campi, tranne le tre
colonne della lista, che legge dalla vista (`v.split_payment`, `v.canale_fe`, `v.pec_email` in
`FornitoriRepository.list_fornitori`). ⛔ Se la vista le perdesse nello stesso giro del catalogo, la lista fornitori
uscirebbe 500 fino al commit del BE. Quindi: giro A (il catalogo non le chiede più) → il BE le toglie dalla SELECT →
giro B (vista e tabella).

## 4. Dopo l'apply, al team BE

Dopo il giro A: via `v.split_payment`, `v.canale_fe`, `v.pec_email` dalla SELECT di
`FornitoriRepository.list_fornitori`, col commento che le spiega; via le chiavi i18n `anagrafiche.fornitori.col_pec_email`,
`col_canale_fe`, `col_split_payment` (le citava solo il catalogo). Poi riparte il DB col giro B.
