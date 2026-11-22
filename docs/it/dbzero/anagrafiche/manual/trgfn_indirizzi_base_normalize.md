## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_indirizzi_base_normalize`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi) — gli indirizzi dei ruoli, su cui è montata
> * [anagrafiche.indirizzi_soggetti](/dbzero/anagrafiche/tabelle/indirizzi_soggetti) — gli indirizzi dei soggetti, su cui è montata
>
> Approfondimento funzioni:
>
> * [script.fn_stato_proposto_id](/dbzero/script/funzioni/fn_stato_proposto_id) — lo stato proposto, quando chi scrive non lo dice
> * [anagrafiche.trgfn_indirizzi_sync_geoloc](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_sync_geoloc) — gira dopo, e riempie la posizione dal civico
> * [anagrafiche.trgfn_indirizzi_guard_forma_libera](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_guard_forma_libera) — gira dopo, e giudica la riga messa in ordine

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_indirizzi_base_normalize` mette in ordine un indirizzo di ruolo o di soggetto secondo la
sua forma, prima che lo si giudichi e lo si salvi. Di suo non rifiuta niente.

---

### Col dettaglio, la riga dimentica la forma libera

Se la riga punta un civico, il trigger svuota testo, stato, comune, CAP, località, area amministrativa,
frazione e codice postale: chi passa all'indirizzo col dettaglio non si porta dietro i pezzi di quello libero,
e il `CHECK` che vuole una forma sola non scatta per un residuo. Svuota anche la posizione, che il trigger
successivo riprende dal civico.

---

### Nella forma libera, il vuoto è nessun valore e lo stato c'è

* Testo, località, codice postale, area amministrativa e frazione perdono gli spazi in testa e in coda, e un
  testo vuoto diventa nessun valore: una località di soli spazi non è una località, e il giudizio della forma
  la vede per quello che è.
* Lo stato non detto è lo stato proposto. La funzione che lo legge si ferma se il parametro manca o non indica
  uno stato solo: non c'è un ripiego.

La posizione scritta da chi salva un indirizzo libero resta com'è.

---

### Codici errore

Nessuno suo. Dallo stato proposto possono arrivare quelli di `script.fn_stato_proposto_id`, quando il parametro
`STATO_PROPOSTO_ISO2` manca o è sbagliato.

---

### Test

* `db/pgtap/anagrafiche/test-indirizzo-libero-due-forme-v1.sql` — l'ordine dei trigger, la località di soli
  spazi che diventa mancante, lo stato non detto che diventa lo stato proposto, il parametro vuoto che ferma la
  scrittura senza ripiego.

---

### Note di migrazione

* 2026-10-18 — porta a nessun valore i testi vuoti della forma libera e scrive lo stato proposto, letto dal
  parametro `STATO_PROPOSTO_ISO2`.

---

{% include-markdown "it/dbzero/anagrafiche/_indirizzo-libero-o-dettaglio.md" %}

---

{% include-markdown "signature-core.md" %}
