## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_indirizzi_soggetti_guard_obbligatori_soggetto`

> **Ultimo aggiornamento**: 24 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.indirizzi_soggetti](/dbzero/anagrafiche/tabelle/indirizzi_soggetti) — la tabella su cui è montato
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — il soggetto giudicato
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_guard_indirizzi_obbligatori_soggetto](/dbzero/anagrafiche/funzioni/fn_guard_indirizzi_obbligatori_soggetto) — il controllo, a cui delega
> * [anagrafiche.trgfn_soggetti_guard_indirizzi_required](/dbzero/anagrafiche/funzioni/trgfn_soggetti_guard_indirizzi_required) — lo stesso controllo quando si scrive il soggetto
> * [anagrafiche.trgfn_indirizzi_guard_obbligatori_ruolo](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_guard_obbligatori_ruolo) — il gemello sugli indirizzi del ruolo

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_indirizzi_soggetti_guard_obbligatori_soggetto` controlla, alla conferma della transazione, che
il soggetto da cui un indirizzo esce, perché cancellato o cambiato di tipo, abbia ancora gli indirizzi che la sua
natura dichiara obbligatori.

---

### La strada dell'indirizzo che se ne va

Una società nata con la sede legale la perde senza che il soggetto si scriva, se si cancella quell'indirizzo o
gliene si cambia il tipo. Questo constraint trigger differito su `anagrafiche.indirizzi_soggetti`, alla DELETE e
all'UPDATE, giudica il soggetto **di prima** dell'indirizzo, con
`anagrafiche.fn_guard_indirizzi_obbligatori_soggetto`.

* Un UPDATE che non cambia né il tipo né il soggetto non chiede niente.
* Il cambio di soggetto arriva qui solo dalla porta di manutenzione: per chiunque altro il titolare di un
  indirizzo è bloccato prima (`E_INDIRIZZO_SOGGETTO_TITOLARE_IMMUTABILE`). Quando passa, il soggetto di prima
  si giudica come dopo una cancellazione.
* Il soggetto cancellato coi suoi indirizzi non si giudica.
* **Si giudica ciò che l'indirizzo dava**: il trigger passa al guard il tipo che esce e il `tx_id` della riga, che
  va al log del rifiuto. Si giudicano solo le righe obbligatorie che quel tipo soddisfaceva, come tipo o come
  ripiego: un soggetto a cui una riga obbligatoria nata dopo chiede un indirizzo che non ha mai avuto può comunque
  cancellare un indirizzo che nessuno chiede.

---

{% include-markdown "it/dbzero/anagrafiche/_indirizzi-obbligatori.md" %}

---

### Codici errore

* `E_INDIRIZZO_OBBLIGATORIO_MANCANTE_TIPO_SOGGETTO` — il soggetto resta senza un indirizzo che la natura chiede;
  lo solleva `anagrafiche.fn_guard_indirizzi_obbligatori_soggetto`.

---

### Test

* `db/pgtap/anagrafiche/test-indirizzi-obbligatori-ripiego-e-cancellazione-v1.sql` — il trigger differito sugli
  eventi giusti; la sede legale di una società, cancellata o cambiata di tipo, rifiutata col codice del
  soggetto; la sostituzione nella stessa transazione, che passa.
* `db/pgtap/anagrafiche/test-indirizzi-obbligatori-requisito-nuovo-v1.sql` (4, 5) — sul soggetto a cui un
  obbligatorio nato dopo chiede un indirizzo che non ha, cancellare un indirizzo che nessuno chiede passa;
  cancellare l'unico indirizzo di una riga obbligatoria si rifiuta.

---

### Note di migrazione

* 2026-11-17 — nasce per la strada della cancellazione e del cambio di tipo, che prima nessuno controllava.
* 2026-11-24 — passa al guard il tipo che esce e il `tx_id` della riga: prima il guard rigiudicava tutto il titolare,
  e il log del rifiuto non diceva la transazione.

---

{% include-markdown "signature-core.md" %}
