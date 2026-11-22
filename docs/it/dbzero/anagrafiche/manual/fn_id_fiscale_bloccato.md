## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_id_fiscale_bloccato`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — i due campi a cui la regola si applica
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_soggetti_guard_id_fiscale_immutabile](/dbzero/anagrafiche/funzioni/trgfn_soggetti_guard_id_fiscale_immutabile) — il guard che rifiuta il cambio
> * [anagrafiche.fn_soggetto_id_fiscale_bloccato](/dbzero/anagrafiche/funzioni/fn_soggetto_id_fiscale_bloccato) — la stessa regola, letta sulla riga per il form
> * [script.fn_is_super_admin](/dbzero/script/funzioni/fn_is_super_admin) — chi è SUPER_ADMIN

---

### 🎯 Scopo Principale

`anagrafiche.fn_id_fiscale_bloccato` dice se un codice fiscale o una partita IVA, dato il loro valore attuale,
sono bloccati: è la regola «CF e P.IVA già scritti non si cambiano», in un posto solo.

---

### Quando un valore è bloccato

Risponde vero quando valgono insieme due cose: il valore è scritto (non NULL), e chi agisce non è SUPER_ADMIN.
Altrimenti risponde falso:

* un valore NULL si può riempire: l'identità del soggetto passa da incompleta a completa, non da un soggetto a
  un altro;
* il SUPER_ADMIN può correggere un errore di battitura.

Chi agisce è l'utente della richiesta, letto dal contesto della sessione; se è SUPER_ADMIN lo dice
`script.fn_is_super_admin`, la stessa regola del backend. Senza utente la risposta è «non è SUPER_ADMIN»: un
valore scritto resta bloccato.

La funzione riceve il valore, non il soggetto: il guard le passa il valore che il campo aveva prima della
scrittura, il form la raggiunge attraverso `anagrafiche.fn_soggetto_id_fiscale_bloccato`, che legge il valore
dalla riga.

---

### Codici errore

Nessuno: risponde vero o falso. Il rifiuto lo solleva il guard (`E_SOGGETTO_ID_FISCALE_IMMUTABILE`).

---

### Test

* `db/pgtap/anagrafiche/test-soggetti-id-fiscale-immutabile-v1.sql` — il guard rifiuta e il form spegne gli
  stessi campi: per l'operatore i campi scritti sono bloccati, per il SUPER_ADMIN no; un campo vuoto si riempie,
  poi è bloccato anche lui.

---

### Note di migrazione

* 2026-11-09 — nasce, con la decisione di Tid: CF e P.IVA scritti non si cambiano, salvo il SUPER_ADMIN; un
  campo vuoto si riempie.

---

{% include-markdown "it/dbzero/anagrafiche/_identificativo-fiscale.md" %}

---

{% include-markdown "signature-core.md" %}
