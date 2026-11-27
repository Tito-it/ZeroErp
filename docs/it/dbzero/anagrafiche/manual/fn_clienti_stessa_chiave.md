## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_clienti_stessa_chiave`

> **Ultimo aggiornamento**: 26 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti) — i clienti che la lettura restituisce
> * [anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account) — da dove viene l'azienda di un billing account
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_guard_cliente_chiave_unica](/dbzero/anagrafiche/funzioni/fn_guard_cliente_chiave_unica) — il rifiuto del doppione, primo lettore
> * [anagrafiche.trgfn_clienti_set_parent_istanza](/dbzero/anagrafiche/funzioni/trgfn_clienti_set_parent_istanza) — la catena delle istanze fittizie, che ne cerca il predecessore
> * [script.fn_get_ba_emittente_sr_id_installazione](/dbzero/script/funzioni/fn_get_ba_emittente_sr_id_installazione) — l'azienda di un billing account per l'installazione
>
> Guide:
>
> * [Un cliente manuale per soggetto, servizio e azienda](/guide/gestione-delle-istanze-utility#un-cliente-manuale-per-soggetto-servizio-e-azienda) — la regola raccontata a chi usa il gestionale

---

### 🎯 Scopo Principale

`anagrafiche.fn_clienti_stessa_chiave` risponde alla domanda «chi occupa già questa fornitura?» per i
clienti senza punto di fornitura: dati un soggetto, un servizio e un'azienda, restituisce i clienti delle
istanze fittizie che li hanno, col codice del loro billing account, lo stato e il periodo.

---

### La risposta porta il periodo, non il giudizio

La lettura dice chi occupa la chiave, non se c'è un conflitto: restituisce il periodo di ciascun cliente, e
la sovrapposizione la decide chi legge. Il rifiuto del doppione confronta i periodi col periodo del cliente
che si sta scrivendo; l'avviso del pre-contrattuale li confronta col giorno in cui l'operatore lo prepara;
la catena delle istanze cerca il cliente più recente. Per questo i clienti escono dal più recente: per data
di attivazione e poi per id, a scendere.

---

### L'azienda è un dato della domanda

Il soggetto e il servizio sono colonne del cliente; l'azienda no: la lettura la ricava per ogni cliente dal
suo billing account, per l'installazione, e la confronta con quella chiesta. Chi chiama passa l'azienda
che vuole controllare (il rifiuto, quella del cliente che sta scrivendo), mai quella di chi sta lavorando.

Ogni billing account ha sempre il suo collegamento a un'azienda, e la risposta è quella del collegamento.
Un billing account non nasce finché l'installazione non ha un'azienda (`E_EMITTENTE_DEFAULT_MISSING`):
un cliente senza azienda non esiste, e la domanda ha sempre un'azienda da confrontare.

---

### Note di migrazione

* 2026-10-14 — nasce con la regola del cliente manuale (decisione di Tid del 2026-10-13), come predicato
  unico del rifiuto, dell'avviso e della catena.

---

{% include-markdown "it/dbzero/anagrafiche/_chiave-unica-cliente.md" %}

---

{% include-markdown "signature-core.md" %}
