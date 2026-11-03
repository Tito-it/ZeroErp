## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_magazzino`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.magazzini](/dbzero/magazzino/tabelle/magazzini) — la riga che la fixture fa nascere
>
> Approfondimento funzioni:
>
> * [magazzino.fn_crea_magazzino](/dbzero/magazzino/funzioni/fn_crea_magazzino) — il building block che scrive la riga
> * [script.fn_pgtap_emittente_operatore](/dbzero/script/funzioni/fn_pgtap_emittente_operatore) — l'emittente dell'operatore in sessione
> * [dbops.fn_pgtap_crea_indirizzo_dettaglio](/dbzero/dbops/funzioni/fn_pgtap_crea_indirizzo_dettaglio) — l'indirizzo fabbricato del magazzino
> * [script.fn_pgtap_set_contesto_operatore](/dbzero/script/funzioni/fn_pgtap_set_contesto_operatore) — il contesto da aprire prima
> * [dbops.fn_pgtap_crea_articolo](/dbzero/dbops/funzioni/fn_pgtap_crea_articolo) — la fixture dell'articolo che si movimenta qui
>
> Guide:
>
> * [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) — dove si sceglie una fixture

---

### 🎯 Scopo Principale

Fixture pgTAP: **un magazzino dell'emittente dell'operatore in sessione**, con un indirizzo
fabbricato e la gestione per ubicazioni scelta dal test (di default spenta).

---

### ⚠️ Va chiamata dopo aver aperto il contesto

Il guard di scope dei magazzini pretende l'emittente dell'operatore, e la fixture lo legge dalla
sessione. Senza un contesto operatore aperto non trova nessun emittente e si ferma con un errore
che dice di aprire prima il contesto: non costruisce un'azienda da sé.

---

### ⭐ La riga la scrive il building block del dominio

Il magazzino nasce da `magazzino.fn_crea_magazzino`, la stessa porta dell'applicazione: unicità
del codice, scope e indirizzo attivo li controllano i presidi di sempre. La fixture sceglie solo
ciò che un test non vuole scegliere: la descrizione (derivata dal codice) e un indirizzo di
dettaglio nuovo, intitolato al codice.

---

### Test

Non ha un test suo: la presidiano i file di magazzino che la usano, per esempio
`db/pgtap/magazzino/test-fn-crea-magazzino-v1.sql`, `db/pgtap/magazzino/test-ddt-scarico-v1.sql`
e `db/pgtap/magazzino/test-ubicazioni-guard-parent-v1.sql`.

---

### Note di migrazione

* 2026-09-18 — nasce con il motore del magazzino (`brief-db-magazzino-lotto-2-motore`).
* 2026-10-18 — la riga non la scrive più un `INSERT` della fixture ma `magazzino.fn_crea_magazzino`
  (regola del 2, `brief-db-processi-accensione-per-ambiente`).

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
