## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_indirizzi_guard_obbligatori_ruolo`

> **Ultimo aggiornamento**: 24 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi) — la tabella su cui è montato
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il ruolo giudicato
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_guard_indirizzi_obbligatori_ruolo](/dbzero/anagrafiche/funzioni/fn_guard_indirizzi_obbligatori_ruolo) — il controllo, a cui delega
> * [anagrafiche.trgfn_soggetti_ruoli_guard_indirizzi_required](/dbzero/anagrafiche/funzioni/trgfn_soggetti_ruoli_guard_indirizzi_required) — lo stesso controllo quando si scrive il ruolo
> * [anagrafiche.trgfn_indirizzi_soggetti_guard_obbligatori_soggetto](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_soggetti_guard_obbligatori_soggetto) — il gemello sugli indirizzi del soggetto

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_indirizzi_guard_obbligatori_ruolo` controlla, alla conferma della transazione, che il ruolo da
cui un indirizzo esce, perché cancellato o cambiato di tipo, abbia ancora i suoi indirizzi obbligatori.

---

### La strada dell'indirizzo che se ne va

Il controllo quando si scrive il ruolo non basta: un ruolo nato completo perde un obbligatorio senza essere
toccato, se si cancella il suo indirizzo o gliene si cambia il tipo. Questo constraint trigger differito su
`anagrafiche.indirizzi`, alla DELETE e all'UPDATE, giudica il ruolo **di prima** dell'indirizzo, con
`anagrafiche.fn_guard_indirizzi_obbligatori_ruolo`.

* Un UPDATE che non cambia né il tipo né il ruolo non chiede niente: il resto dell'indirizzo non conta per il
  requisito.
* Il cambio di ruolo arriva qui solo dalla porta di manutenzione: per chiunque altro il titolare di un
  indirizzo è bloccato prima (`E_INDIRIZZO_RUOLO_TITOLARE_IMMUTABILE`). Quando passa, il ruolo di prima si
  giudica come dopo una cancellazione.
* Cancellare l'indirizzo del tipo quando il ruolo ha quello del ripiego passa: il requisito resta soddisfatto.
* **Si giudica ciò che l'indirizzo dava**: il trigger passa al guard il tipo che esce e il `tx_id` della riga, che
  va al log del rifiuto. Si giudicano solo le righe obbligatorie che quel tipo soddisfaceva, come tipo o come
  ripiego: un ruolo a cui una riga obbligatoria nata dopo chiede un indirizzo che non ha mai avuto può comunque
  cancellare un indirizzo che nessuno chiede.

---

{% include-markdown "it/dbzero/anagrafiche/_indirizzi-obbligatori.md" %}

---

### Codici errore

* `E_INDIRIZZO_OBBLIGATORIO_MANCANTE` — il ruolo resta senza un indirizzo che il requisito chiede; lo solleva
  `anagrafiche.fn_guard_indirizzi_obbligatori_ruolo`.

---

### Test

* `db/pgtap/anagrafiche/test-indirizzi-obbligatori-ripiego-e-cancellazione-v1.sql` — il trigger differito sugli
  eventi giusti; l'unica fatturazione di un cliente, cancellata o cambiata di tipo, rifiutata con la frase del
  ruolo; la cancellazione che il ripiego lascia passare; la sostituzione nella stessa transazione e il ruolo
  cancellato coi suoi indirizzi, che passano.
* `db/pgtap/anagrafiche/test-indirizzi-obbligatori-requisito-nuovo-v1.sql` (7) — sul ruolo a cui un obbligatorio nato
  dopo chiede un indirizzo che non ha, cancellare un indirizzo che nessuno chiede passa.

---

### Note di migrazione

* 2026-11-17 — nasce per la strada della cancellazione e del cambio di tipo, che prima nessuno controllava.
* 2026-11-24 — passa al guard il tipo che esce e il `tx_id` della riga: prima il guard rigiudicava tutto il titolare,
  e il log del rifiuto non diceva la transazione.

---

{% include-markdown "signature-core.md" %}
