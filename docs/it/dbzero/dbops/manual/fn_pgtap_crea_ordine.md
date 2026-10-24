## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_ordine`

> 👀 **Vedi anche**
>
> • [dbops.fn_pgtap_crea_mondo_cliente](/dbzero/dbops/funzioni/fn_pgtap_crea_mondo_cliente) — il mondo su cui questa funzione appoggia la testata
>
> • [dbops.fn_pgtap_crea_preventivo](/dbzero/dbops/funzioni/fn_pgtap_crea_preventivo) — il gemello, per il preventivo
>
Guide: [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) · brief `brief-db-fixture-rls-documenti-costruiti` (giro 2)

---
### 🎯 Scopo Principale

(rev 2026-10-07)

**Un ordine di vendita del mondo, in una chiamata sola**: l'azienda con il suo operatore,
il cliente fatturabile e la testata nello stato scelto. Torna tutte le chiavi, `uid`
compreso (serve a chi lega un documento a valle con la sua sorgente).

```sql
CREATE TEMP TABLE tmp_o AS
SELECT * FROM dbops.fn_pgtap_crea_ordine('rls ordini');
-- un ordine già confermato:
SELECT * FROM dbops.fn_pgtap_crea_ordine('consegne', 'CONFERMATO');
-- il secondo ordine dello STESSO cliente (terzo parametro, rev 2026-10-22):
SELECT * FROM dbops.fn_pgtap_crea_ordine(
           'consegne 2', 'DRAFT', (SELECT billing_account_id FROM tmp_o));
```

⚠️ **Il terzo parametro** è il billing account di un cliente già costruito: serve a chi
vuole due ordini dello stesso cliente. Viene **verificato** dal building block
[dbops.fn_pgtap_cliente_ba_del_mondo](/dbzero/dbops/manual/fn_pgtap_cliente_ba_del_mondo),
come per fattura e contratto: un billing account di un'altra azienda solleva subito.

---
### 🧭 Perché esiste

L'ordine si scriveva a mano in molti pgTAP, ognuno con la sua ricetta: chi pescava cliente
ed emittente dal database (e su uno ricostruito da zero non trovava niente), chi li prendeva
da un mondo costruito ma sceglieva valuta, utility ed emittente a modo suo. Era la stessa
regola scritta più volte (regola del 2): ora ha una sede.

---
### 🔗 Cosa decide la funzione e cosa decide il dominio

* **Il mondo** viene da `fn_pgtap_crea_mondo_cliente`: senza contesto lo costruisce e apre
  il contesto sull'operatore che costruisce; con un contesto aperto riusa l'azienda di chi
  agisce, e ogni chiamata porta un cliente nuovo.
* **L'emittente** è quello del mondo, scritto esplicito: è lo stesso che il guard
  emittente/billing account pretende.
* **La valuta** è la prima del catalogo, scritta esplicita: la catena di default
  («cliente → azienda → gestore») su un database ricostruito non regge da sola. È la stessa
  scelta di `fn_pgtap_crea_fattura`.
* **Numero, anno, registro e momento di fatturazione** non li scrive: li assegnano i
  trigger del dominio, come in produzione.

---
### 🚫 Cosa NON scrive

* **Le righe**: sono il caso del test. Si scrivono **solo in bozza**
  (`brief-db-righe-e-componenti-debiti-residui`, D-1, 2026-10-08).

---
### 🔁 Lo stato: nasce in bozza, poi si porta avanti

(rev 2026-10-24, `brief-modello-documento-vendita` N-1)

Un documento nasce solo nel suo stato iniziale. L'ordine del builder nasce in bozza e, se il
secondo parametro chiede un altro stato, ci arriva per la **matrice dei passaggi**
([`dbops.fn_pgtap_porta_a_stato`](/dbzero/dbops/funzioni/fn_pgtap_porta_a_stato)), sotto i
controlli veri. Un passaggio che pretende ciò che il builder non scrive (le righe, per la
conferma) qui si ferma: allora il test chiede la bozza, scrive le righe e porta avanti da sé.
Uno stato che non esiste viene rifiutato per nome, prima di costruire.

---
### ⚠️ Il contratto sui vincoli differiti

Esce con i vincoli **richiusi** (`IMMEDIATE`), come ogni helper di fixture.

---
### 🧪 Il presidio

`db/pgtap/dbops/test-fn-pgtap-crea-ordine-v1.sql` (7 casi) pinna il **contratto**: la
testata esiste ed è quella tornata, l'emittente è quello del billing account, numero e
registro vengono dal dominio, lo stato è quello chiesto, la seconda chiamata riusa
l'azienda, e uno stato inesistente parla.
