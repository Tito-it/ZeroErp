## 📘 Documentazione Concettuale – Funzione `script.fn_resolve_emittente_sr_id`

> **Ultimo aggiornamento**: 7 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.emittente_modi](/dbzero/dbops/tabelle/emittente_modi) — i modi e le loro strade, gli stessi del gemello fiscale
>
> Approfondimento funzioni:
>
> * [script.fn_resolve_emittente_fiscale_id](/dbzero/script/funzioni/fn_resolve_emittente_fiscale_id) — il gemello che risponde con l'emittente fiscale
> * [vendite.trgfn_event_log_deriva_scope](/dbzero/vendite/funzioni/trgfn_event_log_deriva_scope) — il giornale degli eventi, che la chiama
> * [dbops.fn_genera_risolutori_emittente](/dbzero/dbops/funzioni/fn_genera_risolutori_emittente) — chi scrive il corpo

---

### 🎯 Scopo Principale

La stessa domanda del gemello fiscale, *«di chi è questa riga?»*, **fuori dalla row security**, con
la risposta nell'altra convenzione: il **soggetto-ruolo** dell'emittente, oppure `NULL` se il
riferimento non porta a nessun emittente. Il doppio binario fra id dell'emittente fiscale e
soggetto-ruolo è una scelta dichiarata del progetto.

---

### Stessi modi, stesse strade

I modi sono le righe di [`dbops.emittente_modi`](/dbzero/dbops/tabelle/emittente_modi), gli stessi
del gemello fiscale: cambia solo l'ultima lettura. Una radice in convenzione soggetto-ruolo risponde
con la sua colonna; una radice in convenzione fiscale risponde col soggetto-ruolo di quell'emittente
fiscale.

Il corpo lo genera il migrate dal registro: ⛔ **non si modifica a mano**. Fino al 2026-11-07 la
funzione conosceva tre modi, scritti a mano (`lotto`, `commessa`, `fattura`); ora li conosce tutti.

---

### Regole principali

* ⛔ **Un modo sconosciuto solleva** `E_PARAMETRO_INVALIDO`: nel giornale degli eventi un `NULL` vuol
  dire «riga rifiutata», e un refuso diventerebbe un diario che smette di scrivere senza dirlo.
* Su un valore nullo risponde `NULL`.
* `SECURITY DEFINER` per la stessa ragione del gemello: le strade passano da tabelle sotto row
  security, e «non la vedo» non è «non esiste». `search_path` bloccato. Eseguibile da tutti, perché
  chi scrive un evento deve poterla raggiungere.

---

### Test

`dbops/test-emittente-modi-registro-v1`: il corpo vivo è quello del registro; due salti fino a una
radice in convenzione fiscale danno il soggetto-ruolo dell'emittente.

---

{% include-markdown "signature-core.md" %}
