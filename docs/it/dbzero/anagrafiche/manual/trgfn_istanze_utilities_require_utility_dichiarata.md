# trgfn_istanze_utilities_require_utility_dichiarata

### Scopo

Constraint trigger function `AFTER INSERT DEFERRABLE INITIALLY DEFERRED` su
`anagrafiche.istanze_utilities`: **alla conferma dell'operazione** l'istanza
appena nata deve avere il suo billing account.

Regola (decisione di Tid del 2026-10-08): istanza e billing account nascono
insieme, nella stessa transazione, sempre. Un'istanza senza billing account non
e' uno stato del ciclo di vita, e' un dato fuori regola.

## Schema

`anagrafiche`

## Trigger associato

`trg_istanze_utilities_z90_require_utility_dichiarata_ins` — constraint trigger,
`AFTER INSERT`, `DEFERRABLE INITIALLY DEFERRED`, fase `z90`.

## Logica

Delega ad [`anagrafiche.fn_guard_istanza_ha_ba`](/dbzero/anagrafiche/manual/fn_guard_istanza_ha_ba),
che solleva `E_ISTANZA_SENZA_BA` se l'istanza esiste e non ha nessun billing
account. Lo stesso guard lo chiama il gemello sulla cancellazione del BA
([`trgfn_billing_account_require_istanza_ha_ba`](/dbzero/anagrafiche/manual/trgfn_billing_account_require_istanza_ha_ba)):
la regola si rompe alla nascita dell'istanza o togliendole l'ultimo BA, e il
controllo e' uno solo.

La validazione e' differita: dentro la stessa transazione l'istanza puo' essere
scritta prima del suo billing account.

## Il nome

Funzione e trigger tengono il nome «require_utility_dichiarata»: una utility e'
dichiarata sull'istanza dal billing account di quella utility, e il nome lo
dice ancora.

## Note di migrazione

* **2026-05-01** (Strategia C, refactor preventivi): nasce. Bastava **uno** fra
  tre satelliti — `billing_account`, `istanze_dati_precontrattuali`, `clienti` —
  e con la sola riga precontrattuale l'istanza nasceva senza BA. Codice
  `E_ISTANZA_UTILITY_SENZA_UTILITY`.
* **2026-10-08** (`20261008-56`, brief-db-istanza-nasce-col-ba R-1): pretende il
  billing account. Il satellite `clienti` era gia' un ramo morto (un cliente ha
  il BA della sua istanza per FK composta); la riga precontrattuale ora richiede
  il BA della sua coppia (`fk_idp_billing_account_coppia`). Codice
  `E_ISTANZA_SENZA_BA`; `E_ISTANZA_UTILITY_SENZA_UTILITY` e' obsoleto.

## Test

* `db/pgtap/anagrafiche/test-trgfn-istanze-utilities-require-utility-dichiarata.sql`
* `db/pgtap/anagrafiche/test-istanza-nasce-col-ba-v1.sql`

## Vedi anche

* [Guida: Gestione delle istanze utility — Ogni istanza nasce col suo billing account](/it/guide/gestione-delle-istanze-utility#ogni-istanza-nasce-col-suo-billing-account)
