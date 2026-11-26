## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_get_emittente_fiscale_id`

> **Ultimo aggiornamento**: 26 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account) — il collegamento del billing account e la predefinita
> * [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali) — le aziende
>
> Approfondimento funzioni:
>
> * [script.fn_get_ba_emittente_sr_id](/dbzero/script/funzioni/fn_get_ba_emittente_sr_id) — la regola dei tre livelli, che questa funzione usa
> * [anagrafiche.fn_get_emittente_fiscale_pk](/dbzero/anagrafiche/funzioni/fn_get_emittente_fiscale_pk) — la gemella che restituisce l'`id` dell'emittente
> * [vendite.fn_build_fattura_key](/dbzero/vendite/funzioni/fn_build_fattura_key) — sceglie con questa funzione il registro su cui numerare
> * [vendite.fn_get_or_create_lotto](/dbzero/vendite/funzioni/fn_get_or_create_lotto) — la chiama senza billing account

---

### 🎯 Scopo Principale

`anagrafiche.fn_get_emittente_fiscale_id` dice per quale azienda fattura un billing account, per chi deve
scrivere: restituisce il ruolo dell'emittente e solleva `E_EMITTENTE_DEFAULT_MISSING` quando l'azienda non si
risolve.

---

### ⚠️ Restituisce il ruolo, non l'`id` dell'emittente

Nonostante il nome, il valore è `emittente_soggetto_ruolo_id`, cioè l'`id` di `anagrafiche.soggetti_ruoli`: la
chiave con cui fatture, commesse, registri e listini nominano l'azienda. Chi ha bisogno di
`anagrafiche.emittenti_fiscali.id` (le tabelle con `emittente_fiscale_id`, il perimetro dell'operatore) usa
`anagrafiche.fn_get_emittente_fiscale_pk`. Le due funzioni sono involucri dello stesso lettore e rispondono la
stessa azienda.

---

### La regola non sta qui

Quale azienda lo decide `script.fn_get_ba_emittente_sr_id`, che è la sede unica: la regola è nel blocco qui
sotto. Ogni billing account ha sempre il suo collegamento, e la risposta è quella; gli altri livelli del
lettore (l'azienda di chi agisce in sessione, la predefinita) contano solo nell'istante della nascita, prima
che il collegamento sia scritto. Qui restano due cose sue:

* **un'azienda non risolta è un errore di dominio.** Il lettore restituisce `NULL`; questa funzione lo
  trasforma in `E_EMITTENTE_DEFAULT_MISSING`, perché chi la usa sceglie il registro su cui numerare, e un `NULL`
  vorrebbe dire numerare dove capita. Succede solo quando l'installazione non ha nessuna azienda;
* **senza billing account, la predefinita.** Il lettore risponde `NULL` a un billing account nullo, perché
  «nessun billing account» non è «billing account appena nato». Questa funzione invece ripiega sulla
  predefinita, anche in sessione: un lotto di fatturazione non ha un billing account (raccoglie fatture di
  clienti diversi), e `vendite.fn_get_or_create_lotto` la chiama così.

Non guarda se l'azienda è accesa: un collegamento o una predefinita non possono puntare a un'azienda spenta, e
la gemella `_pk` tiene il filtro solo come difesa.

---

### ⚠️ Che cosa oggi non copre

* **Un billing account che non esiste** non è rifiutato: non ha un collegamento, e la funzione risponde
  l'azienda di chi agisce o la predefinita, come per un billing account nell'istante della sua nascita.

---

### Codici errore

* `E_EMITTENTE_DEFAULT_MISSING` — nessun livello risponde: l'installazione non ha nessuna azienda, e quindi
  nemmeno una predefinita.

---

### Test

* `db/pgtap/anagrafiche/test-emittenti-fiscali.sql` — il billing account nasce collegato e la funzione
  risponde l'azienda del collegamento (test 8 e 9); dopo un cambio d'azienda per modifica del collegamento
  risponde quella nuova (test 12 e 13).
* `db/pgtap/anagrafiche/test-fn-get-emittente-fiscale-pk.sql` — i tre livelli del lettore comune, sulla gemella.

---

### Note di migrazione

* 2026-08-19 — la regola passa a `script.fn_get_ba_emittente_sr_id`. Il ripiego senza billing account resta qui:
  la versione di prima ci arrivava per caso, e i lotti ne dipendevano.
* 2026-09-13 — il lettore ha tre livelli: in sessione, un billing account non ancora collegato è dell'azienda di
  chi agisce.
* 2026-11-26 — ogni billing account ha sempre il suo collegamento: i livelli dopo il primo riguardano solo la
  nascita.

---

{% include-markdown "it/dbzero/anagrafiche/_emittente-del-billing-account.md" %}

---

{% include-markdown "signature-core.md" %}
