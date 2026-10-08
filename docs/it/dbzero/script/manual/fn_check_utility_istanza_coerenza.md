# fn_check_utility_istanza_coerenza

### Scopo

Pure check (boolean, nessun errore) sulla coppia `(istanza_utility_id, utility_id)`:
**true se la coppia ha il suo billing account**.

Una utility e' dichiarata su un'istanza dal billing account di quella utility
(regola di Tid del 2026-10-08, per coppia). La check la usano i punti che devono
sapere se una coppia scelta dall'operatore e' valida prima di scriverla.

## Schema

`script`

## Logica

* `p_istanza_utility_id` o `p_utility_id` NULL → `false`;
* esiste un billing account su quella coppia (`uq_billing_instance_utility`) →
  `true`; altrimenti `false`.

## Perche' una fonte sola

Fino al 2026-10-08 le fonti erano tre: billing account, dati precontrattuali,
cliente. Dalla regola «istanza e billing account nascono insieme, per coppia»
le altre due **implicano** il billing account per FK:

* i dati precontrattuali hanno la FK composta verso il BA della loro coppia
  (`fk_idp_billing_account_coppia`);
* il cliente ha il BA della sua istanza (`billing_account_id` NOT NULL, FK
  composta).

Leggerle ancora sarebbe ripetere il BA tre volte.

⚠️ Non e' la regola del constraint trigger dell'istanza («almeno un BA»):
questa guarda la **coppia**. Per questo resta una funzione a se'.

## Chiamanti

* [`vendite.trgfn_preventivi_guard_utility_istanza_coerenza`](/dbzero/vendite/manual/trgfn_preventivi_guard_utility_istanza_coerenza)
  — parla prima della FK composta del preventivo, con un codice leggibile;
* il backend: filtro del lookup istanze per utility e pre-validazione della
  creazione del preventivo (`istanze_utility_repository`).

## Note di migrazione

* **2026-05-01**: nasce con tre fonti (BA, dati precontrattuali, clienti).
* **2026-10-08** (`20261008-58`, brief-db-istanza-nasce-col-ba R-1): una fonte
  sola, il billing account. Firma e ritorno invariati.

## Vedi anche

* [Guida: Gestione delle istanze utility — Ogni istanza nasce col suo billing account](/it/guide/gestione-delle-istanze-utility#ogni-istanza-nasce-col-suo-billing-account)
