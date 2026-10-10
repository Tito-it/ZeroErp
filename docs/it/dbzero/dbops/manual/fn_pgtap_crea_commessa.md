## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_commessa`

> 👀 **Vedi anche**
>
> • [dbops.fn_pgtap_crea_commessa_attivita](/dbzero/dbops/funzioni/fn_pgtap_crea_commessa_attivita) — l'attività da mettere sulla commessa
>
> • [vendite.fn_get_or_create_commessa](/dbzero/vendite/funzioni/fn_get_or_create_commessa) — la madre che apre la commessa
>
> • [dbops.fn_pgtap_crea_mondo_cliente](/dbzero/dbops/funzioni/fn_pgtap_crea_mondo_cliente) — il mondo su cui la commessa nasce
>
Guide: [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) · brief `brief-db-fixture-rls-documenti-costruiti` (giro 3)

---
### 🎯 Scopo Principale

(rev 2026-10-07)

**Una commessa del mondo, in una chiamata sola**: l'azienda con il suo operatore, il
cliente fatturabile e la commessa, aperta dalla **madre del dominio**. Competenza: il mese
corrente. Torna tutte le chiavi, codice compreso.

```sql
CREATE TEMP TABLE tmp_c AS
SELECT * FROM dbops.fn_pgtap_crea_commessa('rls commesse');
```

---
### 🧭 Perché esiste

La commessa si scriveva a mano in molti pgTAP, con un codice inventato ed emittente e
cliente pescati dal database; altri chiamavano la madre ricopiando dieci argomenti. Era la
stessa regola scritta più volte (regola del 2): ora ha una sede.

---
### 🔗 Cosa decide la funzione e cosa decide il dominio

* **Il mondo** viene da `fn_pgtap_crea_mondo_cliente`: senza contesto lo costruisce e apre
  il contesto sull'operatore che costruisce; con un contesto aperto riusa l'azienda di chi
  agisce, e ogni chiamata porta un cliente nuovo.
* **La commessa** la apre `vendite.fn_get_or_create_commessa`, sempre nuova: **codice,
  emittente e stato iniziale li decide la madre**, come in produzione.
* **La competenza** è il mese corrente, così le attività del builder gemello ci cadono
  dentro.

---
### 🚫 Cosa NON scrive

* **Le attività**: sono il caso del test, o del builder gemello
  `fn_pgtap_crea_commessa_attivita`.
* **Il cambio di stato**: la commessa ha un guard di transizione, e nasce nello stato che
  la madre le dà.

---
### ⚠️ Il contratto sui vincoli differiti

Esce con i vincoli **richiusi** (`IMMEDIATE`), come ogni helper di fixture.

---
### 🧪 Il presidio

`db/pgtap/dbops/test-fn-pgtap-crea-commessa-v1.sql` (6 casi) pinna il **contratto**: la
commessa esiste ed è quella tornata, l'emittente è quello del billing account, la
competenza è il mese corrente, il codice viene dal dominio, e la seconda chiamata riusa
l'azienda.
