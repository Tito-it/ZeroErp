## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_ddt`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.ddt](/dbzero/vendite/tabelle/ddt) — la testata che la fixture scrive
> * [vendite.ddt_indirizzi](/dbzero/vendite/tabelle/ddt_indirizzi) — gli indirizzi che l'emissione pretende
>
> Approfondimento funzioni:
>
> * [script.fn_pgtap_emittente_operatore](/dbzero/script/funzioni/fn_pgtap_emittente_operatore) — l'azienda dell'operatore in sessione, su cui nasce la bolla
> * [script.fn_indirizzi_obbligatori_mancanti](/dbzero/script/funzioni/fn_indirizzi_obbligatori_mancanti) — quali indirizzi servono alla bolla
> * [dbops.fn_pgtap_crea_ddt_senza_ordine](/dbzero/dbops/funzioni/fn_pgtap_crea_ddt_senza_ordine) — la bolla senza ordine con la riga, costruita sopra questa
> * [dbops.fn_pgtap_crea_ddt_da_ordine](/dbzero/dbops/funzioni/fn_pgtap_crea_ddt_da_ordine) — la bolla nata da un ordine
> * [dbops.fn_pgtap_porta_a_stato](/dbzero/dbops/funzioni/fn_pgtap_porta_a_stato) — la strada per portarla fuori dalla bozza
>
> Guide:
>
> * [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) — le fixture e quando usarle

---

### 🎯 Scopo Principale

Una bolla di vendita **in bozza e senza righe**, costruita per un test pgTAP: la testata
dell'azienda dell'operatore in sessione, per il cliente che il test le passa, con la
causale di trasporto, i magazzini scelti e gli indirizzi che l'emissione pretende.

È la base dei test di magazzino: le righe e i prelievi, che sono il loro caso, li scrive il
test.

---

### Che cosa sceglie la fixture e che cosa resta al test

* **L'azienda** è quella dell'operatore in sessione: senza un contesto aperto non c'è
  un'azienda, e la fixture si ferma chiedendo di aprirlo prima.
* **Il cliente** lo passa il test (billing account e soggetto-ruolo del cliente, di solito
  dal suo mondo costruito): la fixture non pesca un cliente dal database.
* **La causale** si sceglie per **codice**, fra quelle attive; una causale che non c'è, o un
  vocabolario degli stati senza la bozza, fermano la fixture.
* **I magazzini** di partenza e di arrivo sono quelli del test; senza, decide il dominio (il
  magazzino predefinito).
* **La data** è quella chiesta, scritta alla nascita; senza, è la data operativa
  dell'azienda.
* **Utility** dal billing account, **valuta** la prima del catalogo.
* **Gli indirizzi** obbligatori della bolla di vendita li scrive con un contenuto di prova:
  è ciò che l'emissione controlla, e senza la bolla non uscirebbe mai dalla bozza.
* **Le righe** non le scrive: sono il caso del test.

---

### ⚠️ Nasce in bozza, e ci resta

Lo stato lo mette la nascita del documento. Per portarla avanti il test scrive le righe e
chiama [dbops.fn_pgtap_porta_a_stato](/dbzero/dbops/funzioni/fn_pgtap_porta_a_stato), che
passa dal verbo della bolla sotto i controlli veri. Chi vuole la bolla senza ordine già con
una riga prezzata e consegnata usa
[dbops.fn_pgtap_crea_ddt_senza_ordine](/dbzero/dbops/funzioni/fn_pgtap_crea_ddt_senza_ordine).

Esce con i vincoli **richiusi** (`IMMEDIATE`), come ogni helper di fixture.

---

### Test

* `db/pgtap/dbops/test-fn-pgtap-crea-ddt-senza-ordine-v1.sql` — la data chiesta è scritta
  alla nascita della bolla.
* La usano i test di magazzino che muovono merce (per esempio
  `db/pgtap/magazzino/test-ddt-scarico-v1.sql`, `db/pgtap/magazzino/test-ddt-trasferimento-v1.sql`):
  il presidio è che la bolla che costruisce sia emettibile una volta scritte le righe.

---

### Note di migrazione

* 2026-09-28 — nasce per i test dello scarico di magazzino da bolla
  (`brief-db-magazzino-lotto-3-scarico-da-ddt`).
* 2026-10-20 — l'ambito degli indirizzi passa al codice della sorgente, `DDT_VENDITA`
  (`brief-db-grammatica-unica-documenti`).
* 2026-10-25 — sesto parametro, la data della bolla alla nascita (`brief-db-pgtap-reso-costruito`).

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
