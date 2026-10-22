## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_fattura`

> 👀 **Vedi anche**
>
> • [dbops.fn_pgtap_crea_mondo_cliente](/dbzero/dbops/funzioni/fn_pgtap_crea_mondo_cliente) — il mondo su cui questa funzione appoggia la testata
>
> • [script.fn_pgtap_registro_fattura](/dbzero/script/funzioni/fn_pgtap_registro_fattura) — il registro coerente con l'emittente di chi agisce
>
Guide: [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) · brief `brief-db-fixture-che-costruiscono-giro-2` (§7)

---
### 🎯 Scopo Principale

(rev 2026-09-23 — D7, lotto 1)

**Una fattura del mondo, in una chiamata sola**: l'azienda con il suo operatore, il
cliente fatturabile, la configurazione della coppia (emittente, utility), il registro
coerente e la testata nello stato scelto. Torna tutte le chiavi.

```sql
CREATE TEMP TABLE tmp_f AS
SELECT * FROM dbops.fn_pgtap_crea_fattura('sistemazioni');
```

---
### 🧭 Perché esiste — quattro anelli, non un INSERT

Una testata fiscale non è «una riga in più». È una catena, e ogni anello è una cosa che
chi scrive il test non può indovinare:

1. il cliente va legato all'azienda di **chi agisce** — lo fa un trigger, guardando la
   sessione — quindi il contesto va aperto prima;
2. la coppia (emittente, utility) va **configurata**, o la testata non è scrivibile;
3. il registro dipende dall'emittente di chi agisce: uno di un'altra azienda viene
   rifiutato da un guard;
4. la valuta si risolve lungo la catena «cliente → azienda → gestore»: su un database
   ricostruito nessuno dei tre anelli regge da solo.

Nove file di `db/pgtap/pagamenti/` chiedevano questa catena e la **pescavano**: su un
database ricostruito non c'è nessuna fattura, e morivano nella fixture.

---
### 🔁 Il terzo parametro: la seconda fattura dello stesso cliente

Senza, ogni chiamata costruisce un cliente nuovo. Un test che vuole **due fatture dello
stesso cliente** — il giro delle sistemazioni, la distinta di correzione — passa il
billing account della prima:

```sql
SELECT * FROM dbops.fn_pgtap_crea_fattura(
           'sistemazioni 2', 'DRAFT', (SELECT billing_account_id FROM tmp_f));
```

⚠️ E viene **verificato**: un billing account di un'altra azienda solleva subito, invece
di produrre una testata che un guard rifiuterà venti righe più in là. Il controllo è il
building block [dbops.fn_pgtap_cliente_ba_del_mondo](/dbzero/dbops/manual/fn_pgtap_cliente_ba_del_mondo),
lo stesso di contratto e ordine.

---
### 🚫 Cosa NON scrive, e il criterio è uno

Entra ciò che ha una **trappola d'ordine**, non ciò che serve spesso:

* **righe, scadenze, contabili, movimenti**: sono il caso del test, e ognuno dei nove
  file li scrive coi propri importi;
* **il cambio di stato**: `vendite.fatture` ha un guard di transizione, e una fixture che
  lo attraversasse proverebbe quello invece del proprio caso. Lo stato si sceglie alla
  nascita, col secondo parametro;
* **i cataloghi** (tipo documento, stato, valuta): su un database ricostruito ci sono, e
  si scelgono con un ordinamento stabile.

---
### ⚠️ Il contratto sui vincoli differiti

Esce con i vincoli **richiusi** (`IMMEDIATE`), come ogni helper di fixture. Chi ha bisogno
della finestra differita la riapre subito dopo e lo dichiara in testa al file.

---
### 🧪 Il presidio

`db/pgtap/dbops/test-fn-pgtap-crea-fattura-v1.sql` (8 casi) pinna il **contratto**: la
testata esiste, il registro è dell'azienda di chi agisce, la coppia è configurata, lo
stato è quello chiesto, il terzo parametro riusa il cliente, e uno stato inesistente parla.
