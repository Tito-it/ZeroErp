## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_preventivo`

> 👀 **Vedi anche**
>
> • [dbops.fn_pgtap_crea_mondo_cliente](/dbzero/dbops/funzioni/fn_pgtap_crea_mondo_cliente) — il mondo su cui questa funzione appoggia la testata
>
> • [dbops.fn_pgtap_crea_ordine](/dbzero/dbops/funzioni/fn_pgtap_crea_ordine) — il gemello, per l'ordine
>
Guide: [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) · brief `brief-db-fixture-rls-documenti-costruiti` (giro 2)

---
### 🎯 Scopo Principale

(rev 2026-10-07)

**Un preventivo del mondo, in una chiamata sola**: l'azienda con il suo operatore, il
cliente fatturabile e la testata nello stato scelto. Torna tutte le chiavi, `uid` compreso.

```sql
CREATE TEMP TABLE tmp_p AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo('rls preventivi');
-- un preventivo già emesso:
SELECT * FROM dbops.fn_pgtap_crea_preventivo('revisioni', 'EMESSO');
```

---
### 🧭 Perché esiste

Il preventivo si scriveva a mano in molti pgTAP, ognuno con la sua ricetta: chi lo pescava
dal database, chi lo scriveva col billing account e chi senza, chi sceglieva validità e
valuta a modo suo. Era la stessa regola scritta più volte (regola del 2): ora ha una sede.

---
### 🔗 Cosa decide la funzione e cosa decide il dominio

* **Il mondo** viene da `fn_pgtap_crea_mondo_cliente`, come per l'ordine.
* **L'emittente** è quello del mondo, scritto esplicito; **istanza e utility** sono quelle
  del billing account. Sono le coppie che i guard del preventivo verificano.
* **La valuta** è la prima del catalogo, scritta esplicita, per la stessa ragione
  dell'ordine e della fattura: il default del dominio su un database ricostruito non regge
  da solo.
* **La validità** è di trenta giorni da oggi: un caso che la vuole diversa la scrive lui.
* **Il numero** non lo scrive: lo genera il trigger del dominio.

---
### 🚫 Cosa NON scrive

* **Le righe**: sono il caso del test. Si scrivono **solo in bozza**
  (`brief-db-righe-e-componenti-debiti-residui`, D-1, 2026-10-08).

---
### 🔁 Lo stato: nasce in bozza, poi si porta avanti

(rev 2026-10-24, `brief-modello-documento-vendita` N-1)

Un documento nasce solo nel suo stato iniziale. Il preventivo del builder nasce in bozza e,
se il secondo parametro chiede un altro stato, ci arriva per la **matrice dei passaggi**
([`dbops.fn_pgtap_porta_a_stato`](/dbzero/dbops/funzioni/fn_pgtap_porta_a_stato)), sotto i
controlli veri. Un passaggio che pretende ciò che il builder non scrive (le righe, per
l'emissione) qui si ferma: allora il test chiede la bozza, scrive le righe e porta avanti da
sé. Uno stato che non esiste viene rifiutato per nome, prima di costruire.

---
### ⚠️ Il contratto sui vincoli differiti

Esce con i vincoli **richiusi** (`IMMEDIATE`), come ogni helper di fixture.

---
### 🧪 Il presidio

`db/pgtap/dbops/test-fn-pgtap-crea-preventivo-v1.sql` (7 casi) pinna il **contratto**: la
testata esiste ed è quella tornata, l'emittente è quello del billing account, il numero
viene dal dominio e la validità parte da oggi, lo stato è quello chiesto, la seconda
chiamata riusa l'azienda, e uno stato inesistente parla.
