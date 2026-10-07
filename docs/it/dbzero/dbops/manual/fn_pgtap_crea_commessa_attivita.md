## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_commessa_attivita`

> 👀 **Vedi anche**
>
> • [dbops.fn_pgtap_crea_commessa](/dbzero/dbops/funzioni/fn_pgtap_crea_commessa) — la commessa su cui scriverla
>
> • [vendite.fn_upsert_commessa_attivita](/dbzero/vendite/funzioni/fn_upsert_commessa_attivita) — la madre che la scrive
>
> • [dbops.fn_pgtap_crea_articolo](/dbzero/dbops/funzioni/fn_pgtap_crea_articolo) — l'articolo, costruito
>
Guide: [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) · brief `brief-db-fixture-rls-documenti-costruiti` (giro 3)

---
### 🎯 Scopo Principale

(rev 2026-10-07)

**Un'attività approvata su una commessa già costruita**, scritta dalla **madre del
dominio**: `APPROVATA` e `NON_EMESSA`, quantità 1, prezzo snapshot fisso (default 10), con
la commessa come sorgente. È la forma da cui l'emissione delle attività fatturabili la
prende.

```sql
CREATE TEMP TABLE tmp_a AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita((SELECT commessa_id FROM tmp_c));
-- un'altra, con un prezzo scelto:
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita((SELECT commessa_id FROM tmp_c), 25);
```

---
### 🧭 Perché esiste

Un'attività di commessa si scriveva a mano in molti pgTAP, con articolo, unità di misura e
istanza pescati dal database; altri chiamavano la madre ricopiando una ventina di
argomenti. Era la stessa regola scritta più volte (regola del 2): ora ha una sede.

---
### 🔗 Cosa decide la funzione e cosa decide il dominio

* **L'articolo** si costruisce (`fn_pgtap_crea_articolo`, non gestito a magazzino): su un
  database ricostruito il catalogo degli articoli è vuoto. La sua unità di misura è quella
  dell'attività.
* **L'istanza di utility** è quella del billing account della commessa.
* **La competenza** è quella della commessa, o il mese corrente se la commessa non ne ha.
* **L'attività** la scrive `vendite.fn_upsert_commessa_attivita`.

---
### 🚫 Cosa NON scrive

* **L'emissione e il legame con la fattura**: sono il caso del test. La catena
  dell'applicazione è: legame della commessa alla sorgente, stato `PRONTA_FATTURAZIONE`,
  `vendite.fn_emit_attivita_fatturabili_da_commessa`. Il legame fra attività fatturabile e
  riga di fattura lo scrive il backend (pipeline di fatturazione), e un test lo fa con lo
  stesso `UPDATE`.
* **Listino, promo, contratto**: il prezzo è uno snapshot fisso passato dal chiamante.

---
### ⚠️ Il contratto sui vincoli differiti

Esce con i vincoli **richiusi** (`IMMEDIATE`). Una commessa che non esiste viene rifiutata
per nome.

---
### 🧪 Il presidio

`db/pgtap/dbops/test-fn-pgtap-crea-commessa-attivita-v1.sql` (6 casi) pinna il
**contratto**: l'attività è sulla commessa, approvata e non emessa, con l'istanza del
billing account e la competenza della commessa, il prezzo è quello chiesto, **l'emissione
la prende**, e una commessa inesistente parla.
