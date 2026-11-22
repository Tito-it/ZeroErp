## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_soggetti_ruoli_guard_indirizzi_required`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — la tabella su cui è montato
> * [anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi) — gli indirizzi che il ruolo deve avere
> * [config.tipi_ruolo_tipi_indirizzo](/dbzero/config/tabelle/tipi_ruolo_tipi_indirizzo) — la matrice del tipo di ruolo
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_guard_indirizzi_obbligatori_ruolo](/dbzero/anagrafiche/funzioni/fn_guard_indirizzi_obbligatori_ruolo) — il controllo, a cui delega
> * [anagrafiche.fn_indirizzi_obbligatori_ruolo](/dbzero/anagrafiche/funzioni/fn_indirizzi_obbligatori_ruolo) — il requisito, sulla natura del soggetto
> * [anagrafiche.trgfn_indirizzi_guard_obbligatori_ruolo](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_guard_obbligatori_ruolo) — lo stesso controllo quando un indirizzo se ne va
> * [anagrafiche.trgfn_soggetti_guard_obbligatori_ruoli](/dbzero/anagrafiche/funzioni/trgfn_soggetti_guard_obbligatori_ruoli) — lo stesso controllo quando cambia la natura
> * [anagrafiche.trgfn_soggetti_guard_indirizzi_required](/dbzero/anagrafiche/funzioni/trgfn_soggetti_guard_indirizzi_required) — il gemello del livello soggetto
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — la regola R9, gli indirizzi obbligatori

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_soggetti_ruoli_guard_indirizzi_required` controlla, alla conferma della transazione, che il
ruolo scritto abbia gli indirizzi che il suo tipo di ruolo chiede sulla natura del soggetto, o il loro ripiego.

---

### Quando scatta

È un constraint trigger differito su `anagrafiche.soggetti_ruoli`, all'INSERT e a **ogni** UPDATE. Copre la
nascita del ruolo, che riceve i suoi indirizzi nella stessa transazione (di solito dalla copia degli
obbligatori di [fn_crea_indirizzi_ruolo](/dbzero/anagrafiche/funzioni/fn_crea_indirizzi_ruolo)), e ogni sua
modifica, compresa quella del tipo di ruolo, da cui dipende il requisito.

Il trigger passa il ruolo e il suo `tx_id` a `anagrafiche.fn_guard_indirizzi_obbligatori_ruolo`, la sede unica
del controllo del livello ruolo, che chiamano anche il trigger della cancellazione di un indirizzo e quello del
cambio di natura del soggetto.

---

{% include-markdown "it/dbzero/anagrafiche/_indirizzi-obbligatori.md" %}

---

### ⚠️ Che cosa oggi non copre

* **Un ruolo rimasto incompleto non si modifica più.** Una riga della matrice che diventa obbligatoria o entra
  nella sua validità non rigiudica i ruoli che esistono; alla prima scrittura del ruolo, in qualunque colonna,
  il trigger lo rifiuta finché nella stessa transazione non riceve l'indirizzo che manca.

---

### Codici errore

* `E_INDIRIZZO_OBBLIGATORIO_MANCANTE` — manca un indirizzo che il requisito del ruolo chiede; lo solleva
  `anagrafiche.fn_guard_indirizzi_obbligatori_ruolo`, sul primo tipo mancante.

---

### Test

* `db/pgtap/anagrafiche/test-indirizzo-obbligatorio-mancante-frase-v1.sql` — il codice del livello ruolo e la
  frase intera, senza ripiego e col ripiego.
* `db/pgtap/anagrafiche/test-indirizzi-obbligatori-ripiego-e-cancellazione-v1.sql` — il trigger che chiama il
  guard senza copie della regola, il fornitore privato che nasce completo col solo ripiego.
* `db/pgtap/anagrafiche/create-cliente.sql` — il cliente che nasce coi suoi indirizzi obbligatori.

---

### Note di migrazione

* 2026-11-17 — il controllo passa in `anagrafiche.fn_guard_indirizzi_obbligatori_ruolo`, sul requisito letto
  sulla natura del soggetto, condiviso coi trigger della cancellazione di un indirizzo e del cambio di natura;
  la frase nomina ruolo e tipi per descrizione.

---

{% include-markdown "signature-core.md" %}
