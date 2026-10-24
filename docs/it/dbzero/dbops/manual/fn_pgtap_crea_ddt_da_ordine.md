## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_ddt_da_ordine`

> 👀 **Vedi anche**
>
> • [vendite.fn_genera_ddt_da_ordine](/dbzero/vendite/funzioni/fn_genera_ddt_da_ordine) — la madre da cui nasce la bolla
>
> • [dbops.fn_pgtap_crea_ordine](/dbzero/dbops/funzioni/fn_pgtap_crea_ordine) — l'ordine da cui parte
>
> • [dbops.fn_pgtap_porta_a_stato](/dbzero/dbops/funzioni/fn_pgtap_porta_a_stato) — la strada per portarla avanti
>
> • [dbops.fn_pgtap_crea_ddt](/dbzero/dbops/funzioni/fn_pgtap_crea_ddt) — la bolla in bozza senza ordine, per il magazzino
>
Guide: [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) · brief `brief-db-pgtap-bolla-e-reso-costruiti` (giro 1)

---
### 🎯 Scopo Principale

(rev 2026-10-25)

**Una bolla nata da un ordine confermato, già consegnata, in una chiamata sola.** È il
punto di partenza di tutto ciò che viene dopo la consegna: il reso, l'accredito, la
situazione della merce, la fatturazione delle bolle.

```sql
CREATE TEMP TABLE tmp_b AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('resi');

-- due spedizioni dalla stessa riga d'ordine, 4 e 6
CREATE TEMP TABLE tmp_s1 AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('sped', p_quantita => 10, p_qta_da_evadere => 4);
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine(
           'sped', p_ordine_id => (SELECT ordine_id FROM tmp_s1), p_qta_da_evadere => 6);

-- la bolla in bozza, per scriverle ciò che il test prova, poi consegnata
CREATE TEMP TABLE tmp_d AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('riga a mano', 'DRAFT');
-- … la riga aggiunta a mano …
SELECT dbops.fn_pgtap_porta_a_stato('vendite.ddt', (SELECT ddt_id FROM tmp_d), 'CONSEGNATO');
```

---
### 🧭 Perché esiste

Per avere una bolla consegnata i test ripetevano a mano cinque passi in un ordine
obbligato: l'ordine con la riga, la conferma, la bolla dall'ordine, l'indirizzo e la
causale che la consegna pretende, i passaggi di stato uno per uno. Ognuno con i suoi
controlli, e ogni file li riscriveva per conto suo: quando una regola cambiava, si
correggevano tutte le copie. Ora la strada ha una sede.

---
### 🔗 Cosa decide la funzione e cosa decide il dominio

* **L'ordine** lo costruisce `dbops.fn_pgtap_crea_ordine`, in bozza, con **una** riga
  (`p_quantita`, default 10, a `p_prezzo`, default 25) dell'articolo `p_articolo_id` o di
  uno costruito (merce non gestita). Il **trigger di fatturazione** (`p_fatturazione_trigger`)
  si scrive in bozza, perché fuori bozza è congelato; senza, resta quello del cliente. Poi la
  conferma, per la matrice.
* **Il cliente** è quello del terzo parametro (il billing account di un'altra fixture) o uno
  nuovo, nella stessa azienda di chi agisce.
* **La bolla** la fa la madre `vendite.fn_genera_ddt_da_ordine`, come in produzione: copia
  le righe, scrive il legame con la riga d'ordine e proietta l'ordine a evaso o
  parzialmente evaso. Si evade tutto il residuo, oppure `p_qta_da_evadere` (per l'unica riga
  dell'ordine) o `p_righe` (la grammatica della madre), alla data `p_data`.
* **La data dell'ordine** (`p_data_ordine`) la scrive `dbops.fn_pgtap_crea_ordine` alla
  nascita; senza, è la data operativa. Chi dà alla bolla una data passata dà anche quella
  dell'ordine, così la bolla non è più vecchia del suo ordine.
* **Ciò che l'emissione pretende**: la causale per codice (`p_causale_codice`, default
  `VENDITA`) e gli indirizzi obbligatori della bolla che l'ordine non le ha passato.
* **Lo stato** (default `CONSEGNATO`) si raggiunge per la matrice dei passaggi, sotto i
  controlli veri.
* **Un ordine speciale** — più righe, un kit coi componenti, una data che il test misura —
  lo costruisce il test, lo conferma, e passa `p_ordine_id`: la bolla nasce da lì. Cliente,
  riga, data e trigger sono allora dell'ordine, e passarli è un errore.

Restituisce la bolla, la sua **prima** riga con la quantità, l'ordine e la riga d'ordine
evasa, l'articolo, il cliente, l'azienda, l'operatore e lo stato.

---
### 🚫 Cosa NON fa

* **Non lavora sulla bolla in bozza al posto del test**: una riga aggiunta a mano, un legame
  in più, un prezzo tolto sono il caso del test. Si chiede la bolla in `DRAFT`, si scrive, e
  la si porta avanti con `dbops.fn_pgtap_porta_a_stato`.
* **Non annulla.** Uno stato abortito (`ANNULLATO`) si rifiuta prima di costruire: la
  bolla nata da un ordine ha i legami con le righe d'ordine, e il suo annullo li dichiara
  il verbo `vendite.fn_annulla_ddt`. Si chiede la bolla `EMESSO` e si annulla dal test.
* **Non sostituisce `dbops.fn_pgtap_crea_ddt`**, la bolla in bozza senza ordine per i test
  del magazzino.

---
### ⚠️ Il contratto sui vincoli differiti

Esce con i vincoli **richiusi** (`IMMEDIATE`), come ogni helper di fixture. Senza un
contesto aperto, il mondo lo apre sull'operatore che costruisce.

---
### 🧪 Il presidio

`db/pgtap/dbops/test-fn-pgtap-crea-ddt-da-ordine-v1.sql` (15 casi): firma; bolla consegnata
nata dall'ordine, col numero; legame fra le due righe; ordine evaso, causale e indirizzi;
bolla in bozza; due spedizioni dalla stessa riga; trigger di fatturazione e cliente del
test; causale scelta; la data dell'ordine; quattro errori del chiamante e uno stato
abortito rifiutati.
