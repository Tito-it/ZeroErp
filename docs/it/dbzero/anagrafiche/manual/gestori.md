## 📘 Documentazione Concettuale – Tabella `anagrafiche.gestori`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il ruolo `GE` a cui la riga si aggancia
> * [anagrafiche.gestori_utilities](/dbzero/anagrafiche/tabelle/gestori_utilities) — i servizi del gestore
> * [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali) — chi emette i documenti, che non è il gestore
> * [config.valute](/dbzero/config/tabelle/valute) — la valuta del gestore
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_gestori_guard](/dbzero/anagrafiche/funzioni/trgfn_gestori_guard) — un solo gestore, con partita IVA
> * [anagrafiche.trgfn_gestori_guard_ruolo_gestore](/dbzero/anagrafiche/funzioni/trgfn_gestori_guard_ruolo_gestore) — il ruolo dev'essere `GE`
> * [vendite.fn_get_valuta_id](/dbzero/vendite/funzioni/fn_get_valuta_id) — l'ultimo gradino della valuta di un documento
>
> Guide:
>
> * [Soggetti e ruoli anagrafici](/guide/soggetti-e-ruoli-anagrafici) — il modello soggetto, ruolo, specializzazione

---

### 🎯 Scopo Principale

`anagrafiche.gestori` è la specializzazione del ruolo **gestore** (`GE`): la società che gestisce il sistema
informativo. La tabella ha al più una riga.

---

### Il gestore è un ruolo, non una colonna sul soggetto

Come le altre specializzazioni, la riga nomina con `soggetto_ruolo_id` il legame «questo soggetto è il gestore»
in `anagrafiche.soggetti_ruoli`; il soggetto si raggiunge da lì, e la tabella non ha una colonna propria che lo
nomini. Un ruolo ha al più una riga di gestore (`uq_gestori_soggetto_ruolo`). Che il legame sia proprio del ruolo
`GE` lo controlla `anagrafiche.trgfn_gestori_guard_ruolo_gestore`.

Il gestore non è l'**emittente fiscale**: il primo è chi gestisce il sistema, il secondo chi emette i documenti, e
in un'installazione con più aziende gli emittenti sono più d'uno. Le due cose possono cadere sullo stesso
soggetto, con due ruoli diversi.

---

### ⭐ Uno solo, con partita IVA

`anagrafiche.trgfn_gestori_guard` tiene due regole del ruolo, a ogni nascita e modifica della riga:

* **un solo gestore nel sistema**: una seconda riga è rifiutata, la modifica di quella che c'è no. Nessun vincolo
  di tabella lo dice: la regola sta nel guard;
* **il soggetto del gestore ha la partita IVA**.

Il gestore non ha `attivo` e non si cancella: la cancellazione passa solo dalla porta di manutenzione del
migratore (`script.trgfn_delete_block_by_guc`), e con servizi collegati si ferma comunque sulla chiave esterna di
`anagrafiche.gestori_utilities`.

---

### Che cosa porta

* `descrizione` è il nome breve con cui il gestore si mostra; `cd_prod_software` il codice del prodotto software
  in uso. Tutte e due obbligatorie e non vuote. Nessun oggetto del database legge `cd_prod_software`.
* `valuta_id` è la valuta del gestore, ed è l'ultimo ripiego della valuta di un documento: quando né il billing
  account né l'emittente ne indicano una, `vendite.fn_get_valuta_id` prende quella del gestore.

La tabella non ha storico né identificativo esterno: porta solo l'audit di chi ha scritto e quando.

---

### ⚠️ Che cosa oggi non copre

* **Due nascite contemporanee.** Il «gestore unico» è una lettura del guard, non un vincolo: due transazioni che
  inseriscono insieme non vedono l'una la riga dell'altra, e passano tutte e due.
* **La partita IVA tolta dopo.** Il guard la guarda quando si scrive il gestore: un soggetto che la perde in
  seguito resta gestore, e nessun trigger su `anagrafiche.soggetti` lo rileva.

---

### Codici errore

* `E_GESTORE_SOGGETTO_RUOLO_MANCANTE`, `E_RUOLO_RICHIEDE_PIVA`, `E_GESTORE_SINGLETON_VIOLATO` — dal guard di
  dominio (vedi la sua scheda).
* `E_SOGGETTI_RUOLI` — il ruolo non è `GE`.
* `E_DELETE_NOT_ALLOWED` — una cancellazione fuori dalla porta di manutenzione.

---

### Test

* `db/pgtap/anagrafiche/create-soggetto-gestori.sql` — il soggetto col ruolo gestore, il gestore unico, il secondo
  gestore rifiutato. Il file è fra i rossi noti della baseline.
* `db/pgtap/vendite/test-fn-get-valuta-id-v1.sql` — la valuta del gestore come ultimo ripiego.

---

### Note di migrazione

* 2026-10-08 — nasce `uq_gestori_soggetto_ruolo`, una riga per ruolo, come le altre specializzazioni.
* 2026-10-10 — si ritira `uq_gestori_singleton`, che nonostante il nome non vincolava niente: il gestore unico è
  sempre stato del guard.

---

{% include-markdown "signature-core.md" %}
