## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_check_ba_coppia_emittente_omogenea`

> **Ultimo aggiornamento**: 26 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — i due billing account confrontati
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_get_emittente_fiscale_id](/dbzero/anagrafiche/funzioni/fn_get_emittente_fiscale_id) — l'azienda risolta di ciascuno
> * [anagrafiche.fn_guard_albero_ba_emittente](/dbzero/anagrafiche/funzioni/fn_guard_albero_ba_emittente) — chiamante: padre e figli
> * [anagrafiche.fn_guard_istanza_ba_emittente](/dbzero/anagrafiche/funzioni/fn_guard_istanza_ba_emittente) — chiamante: i billing account della stessa istanza

---

### 🎯 Scopo Principale

`anagrafiche.fn_check_ba_coppia_emittente_omogenea` risponde sì o no: questi due billing account sono della
stessa azienda? Non solleva un verdetto proprio: è il confronto su cui poggiano il guard dell'albero e quello
dell'istanza.

---

### Un albero non attraversa due aziende; un soggetto sì

Un soggetto può essere cliente di più aziende, con alberi di billing account separati: è legittimo. Ciò che
non deve esistere è **un** albero, o **una** istanza, con billing account di due aziende, perché la fattura e
la visibilità prendono l'azienda da lì. La domanda è quindi sulla coppia, non sul soggetto.

---

### ⭐ L'azienda si risolve, con la regola della fatturazione

Ciascuno dei due passa da `anagrafiche.fn_get_emittente_fiscale_id`, la funzione con cui la fatturazione
sceglie il registro, così «coppia omogenea» e «la fattura esce da una sola azienda» sono la stessa
affermazione. Ogni billing account ha sempre il suo collegamento, e la risposta è l'azienda del collegamento:
per chi agisce e per l'installazione è la stessa.

I nomi dei parametri parlano di figlio e padre perché la check è nata per l'albero; il confronto non dipende
dal verso, e per due billing account della stessa istanza vale identico.

* Senza secondo billing account la risposta è sì: non c'è coppia.
* Lo stesso billing account due volte è sì: l'autoriferimento lo rifiuta altrove (`E_PARENT_SELF`).
* Un'azienda non risolta è no: nel dubbio si chiude.
* `E_EMITTENTE_DEFAULT_MISSING`, quando non c'è nemmeno la predefinita, risale com'è: è un difetto di
  configurazione, e mascherarlo lo renderebbe invisibile.

---

### Test

* `db/pgtap/anagrafiche/test-guard-albero-ba-omogeneo-v1.sql` — alberi omogenei che passano, coppie miste in
  ogni verso rifiutate dai guard che la chiamano, due alberi separati dello stesso soggetto ammessi; lo
  spostamento della predefinita lascia padre e figlio sulla loro azienda.

---

### Note di migrazione

* 2026-08-18 — nasce col controllo dell'albero omogeneo.
* 2026-10-08 — diventa anche il confronto dei billing account della stessa istanza.
* 2026-11-26 — con ogni billing account collegato il confronto risponde sempre col collegamento: il caso del
  billing account scollegato confrontato con l'azienda di chi agisce non esiste più.

---

{% include-markdown "it/dbzero/anagrafiche/_emittente-del-billing-account.md" %}

---

{% include-markdown "signature-core.md" %}
