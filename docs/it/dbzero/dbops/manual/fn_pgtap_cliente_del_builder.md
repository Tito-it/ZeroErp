## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_cliente_del_builder`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_pgtap_crea_mondo_cliente](/dbzero/dbops/funzioni/fn_pgtap_crea_mondo_cliente) — il mondo, quando il test non passa un cliente
> * [dbops.fn_pgtap_azienda_di_chi_agisce](/dbzero/dbops/funzioni/fn_pgtap_azienda_di_chi_agisce) — l'azienda del contesto, quando il test passa il suo cliente
> * [dbops.fn_pgtap_cliente_ba_del_mondo](/dbzero/dbops/funzioni/fn_pgtap_cliente_ba_del_mondo) — la verifica del billing account del test
>
> Guide:
>
> * [Come si scrive un test pgTAP](/guide/pgtap-come-si-scrive-un-test) — i builder che ricevono il billing account di un'altra fixture

---

### 🎯 Scopo Principale

Il cliente su cui scrive un builder di documento: senza billing account il mondo (azienda,
operatore, contesto e un cliente nuovo); con il billing account di un'altra fixture,
l'azienda di chi agisce e quel conto, verificato, **senza** un cliente nuovo.

La chiamano i builder di commessa, contratto, fattura, ordine, lotto e bolla senza ordine;
non si chiama dal test.

---

### ⭐ Col conto del test non nasce un cliente in più

Il mondo costruisce sempre un cliente. Un builder che lo chiamasse anche quando il test gli
passa il suo conto lascerebbe a ogni chiamata un cliente che nessuno usa: non rompe niente,
ma sporca l'azienda del test e le viste che ne contano i clienti. Per questo i due casi
hanno due strade:

* **senza conto** — [fn_pgtap_crea_mondo_cliente](/dbzero/dbops/funzioni/fn_pgtap_crea_mondo_cliente),
  con l'etichetta del builder;
* **con il conto** — l'azienda da
  [fn_pgtap_azienda_di_chi_agisce](/dbzero/dbops/funzioni/fn_pgtap_azienda_di_chi_agisce) e
  la verifica da [fn_pgtap_cliente_ba_del_mondo](/dbzero/dbops/funzioni/fn_pgtap_cliente_ba_del_mondo):
  un conto di un'altra azienda solleva, nominando il builder (`p_chiamante`).

---

### ⚠️ Col conto del test serve un contesto aperto

L'azienda di chi agisce esiste solo con un contesto aperto: senza, la funzione solleva e lo
dice. È lo stesso esito di prima con un messaggio migliore, perché il mondo senza contesto
costruirebbe un'azienda nuova, e il conto del test, che è di un'altra, verrebbe rifiutato
comunque.

---

### Codici errore

Nessuno suo: i rifiuti sono quelli, senza codice, dei due building block che compone.

---

### Test

* `db/pgtap/dbops/test-fn-pgtap-cliente-del-builder-v1.sql` — senza contesto l'azienda non
  c'è; senza conto il mondo, con un cliente nuovo; col conto del test lo stesso cliente e la
  stessa azienda, e nessun cliente in più nemmeno passando dai builder, che scrivono sul
  cliente chiesto; un conto di un'altra azienda è rifiutato.

---

### Note di migrazione

* 2026-10-24 — prende il posto del blocco che i builder ricopiavano (costruire il mondo,
  poi verificare il conto del test), che lasciava un cliente in più a ogni chiamata
  (`brief-modello-documento-vendita`, §4-octies).

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
