## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_ddt_senza_ordine`

> 👀 **Vedi anche**
>
> • [dbops.fn_pgtap_crea_ddt](/dbzero/dbops/funzioni/fn_pgtap_crea_ddt) — la testata in bozza su cui si appoggia
>
> • [dbops.fn_pgtap_crea_ddt_da_ordine](/dbzero/dbops/funzioni/fn_pgtap_crea_ddt_da_ordine) — il gemello, per la bolla nata da un ordine
>
> • [dbops.fn_pgtap_porta_a_stato](/dbzero/dbops/funzioni/fn_pgtap_porta_a_stato) — la strada per portarla avanti
>
Guide: [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) · brief `brief-db-pgtap-reso-costruito` (E-5)

---
### 🎯 Scopo Principale

(rev 2026-10-25)

**Una bolla senza ordine dietro, con una riga prezzata, già consegnata, in una chiamata sola.**

```sql
CREATE TEMP TABLE tmp_b AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_senza_ordine('rls resi',
           p_billing_account_id => (SELECT billing_account_id FROM _m));

-- in bozza, a una data, con la causale del caso
SELECT * FROM dbops.fn_pgtap_crea_ddt_senza_ordine('visione', 'DRAFT',
           p_causale_codice => 'CONTO_VISIONE', p_data => DATE '2101-01-15');
```

---
### 🧭 Perché esiste

Per uscire dalla bozza una bolla senza ordine pretende una riga, e la riga deve portare da
sé prezzo e aliquota: senza ordine non c'è da dove ereditarli. Una dozzina di test
scrivevano a mano testata, indirizzo, causale, riga e passaggi di stato. Il builder della
testata (`fn_pgtap_crea_ddt`) dà la bozza senza righe, che serve al magazzino: mancava proprio
il passo con la trappola.

---
### 🔗 Cosa decide la funzione e cosa decide il dominio

* **Il cliente** è quello del test (terzo parametro) o uno nuovo, nell'azienda di chi agisce.
* **La testata** la fa `dbops.fn_pgtap_crea_ddt`: causale per codice, magazzino, data alla
  nascita, indirizzi obbligatori.
* **La riga**: `p_quantita` (default 10) a `p_prezzo` (default 25), con la prima aliquota
  attiva, dell'articolo del test o di uno costruito.
* **Lo stato** (default `CONSEGNATO`) per la matrice dei passaggi, sotto i controlli veri.

---
### 🚫 Cosa NON fa

* **Non muove merce**: un articolo gestito a magazzino si rifiuta. I test che muovono merce
  scrivono righe e prelievi da sé, sulla bozza di `fn_pgtap_crea_ddt`: sono il loro caso.
* **Non annulla**: uno stato abortito si rifiuta. L'annullo è del verbo `vendite.fn_annulla_ddt`.

---
### ⚠️ Il contratto sui vincoli differiti

Esce con i vincoli **richiusi** (`IMMEDIATE`), come ogni helper di fixture.

---
### 🧪 Il presidio

`db/pgtap/dbops/test-fn-pgtap-crea-ddt-senza-ordine-v1.sql` (8 casi): firma; bolla consegnata
senza ordine, col numero; la riga prezzata su un articolo merce; causale e indirizzi; bozza,
data e causale scelte; la data alla nascita del builder della testata; merce gestita e stato
abortito rifiutati.
