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

(rev 2026-10-24)

**Una commessa del mondo, in una chiamata sola**: l'azienda con il suo operatore, il
cliente fatturabile e la commessa, aperta dalla **madre del dominio**, nello stato che il
test chiede. Competenza: il mese corrente. Torna tutte le chiavi, codice compreso,
l'attività scritta (se c'è) e lo stato raggiunto.

```sql
CREATE TEMP TABLE tmp_c AS
SELECT * FROM dbops.fn_pgtap_crea_commessa('rls commesse');

-- una commessa emittibile del cliente di un'altra fixture
CREATE TEMP TABLE tmp_e AS
SELECT * FROM dbops.fn_pgtap_crea_commessa(
           'pull', 'PRONTA_FATTURAZIONE', (SELECT billing_account_id FROM tmp_cliente));
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
### 🔁 I quattro parametri in coda

| Parametro | Che cosa fa |
| --- | --- |
| stato (secondo) | lo stato da raggiungere. Vuoto, o lo stato iniziale: la commessa resta lì. Un altro: ci arriva per la **matrice dei passaggi** (`dbops.fn_pgtap_porta_a_stato`), sotto i controlli veri |
| conto di fatturazione (terzo) | la commessa nasce sul cliente di un'altra fixture invece che su uno nuovo. Il conto viene verificato da [dbops.fn_pgtap_cliente_ba_del_mondo](/dbzero/dbops/manual/fn_pgtap_cliente_ba_del_mondo): uno di un'altra azienda solleva subito |
| con attività (quarto) | scrive **un'attività** approvata e non emessa (`fn_pgtap_crea_commessa_attivita`) **prima** del passaggio di stato. Se non lo si dice, la scrive solo quando lo stato chiesto non è l'iniziale: uscire dalla bozza la pretende (una commessa pronta per la fatturazione deve avere almeno una riga approvata) |
| con sorgente ROOT (quinto) | scrive la **sorgente principale** della commessa (la commessa è la radice di se stessa: sorgente `COMMESSA`, chiave il suo id), quella che il giro di fatturazione pretende. Di default no (rev 2026-10-24, R-3) |

⚠️ Senza attività (`false`) l'uscita dalla bozza la ferma il controllo vero, non il
builder: è il caso del test che vuole provarlo.

---
### 🚫 Cosa NON scrive

* **Le attività oltre la prima**, e quelle con forme particolari (già emesse, da approvare,
  con altre quantità): sono il caso del test, o del builder gemello
  `fn_pgtap_crea_commessa_attivita`.
* **Le altre sorgenti** della commessa (i documenti da cui nasce): sono il caso del test.

---
### ⚠️ Il contratto sui vincoli differiti

Esce con i vincoli **richiusi** (`IMMEDIATE`), come ogni helper di fixture.

---
### 🧪 Il presidio

`db/pgtap/dbops/test-fn-pgtap-crea-commessa-v1.sql` (13 casi) pinna il **contratto**: la
commessa esiste ed è quella tornata, l'emittente è quello del billing account, la
competenza è il mese corrente, il codice viene dal dominio, la seconda chiamata riusa
l'azienda; senza stato resta nello stato iniziale senza attività; lo stato emittibile si
raggiunge sul cliente chiesto con un'attività approvata; senza attività lo ferma il
controllo vero; uno stato che non c'è solleva; senza richiesta nessuna sorgente ROOT, e a richiesta una
sola, di tipo commessa.
