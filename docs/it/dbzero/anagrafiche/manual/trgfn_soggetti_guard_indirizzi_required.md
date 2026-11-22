## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_soggetti_guard_indirizzi_required`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — la tabella su cui è montato
> * [anagrafiche.indirizzi_soggetti](/dbzero/anagrafiche/tabelle/indirizzi_soggetti) — gli indirizzi che il soggetto deve avere
> * [config.tipi_soggetto_dettaglio_tipi_indirizzo](/dbzero/config/tabelle/tipi_soggetto_dettaglio_tipi_indirizzo) — la matrice della natura, coi tipi obbligatori
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_guard_indirizzi_obbligatori_soggetto](/dbzero/anagrafiche/funzioni/fn_guard_indirizzi_obbligatori_soggetto) — il controllo, a cui delega
> * [anagrafiche.trgfn_indirizzi_soggetti_guard_obbligatori_soggetto](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_soggetti_guard_obbligatori_soggetto) — lo stesso controllo quando un indirizzo se ne va
> * [anagrafiche.trgfn_soggetti_ruoli_guard_indirizzi_required](/dbzero/anagrafiche/funzioni/trgfn_soggetti_ruoli_guard_indirizzi_required) — il gemello del livello ruolo
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — la regola R9, gli indirizzi obbligatori

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_soggetti_guard_indirizzi_required` controlla, alla conferma della transazione, che il
soggetto scritto abbia gli indirizzi che la sua natura dichiara obbligatori, o il loro ripiego.

---

### Quando scatta

È un constraint trigger differito su `anagrafiche.soggetti`, all'INSERT e a **ogni** UPDATE, qualunque colonna
cambi. Copre così la nascita del soggetto, che riceve i suoi indirizzi nella stessa transazione, e il cambio di
natura, che può chiedere tipi che la natura di prima non chiedeva: si giudica lo stato finale.

Il trigger non decide niente: passa il soggetto e il suo `tx_id` a
`anagrafiche.fn_guard_indirizzi_obbligatori_soggetto`, la sede unica del controllo del livello soggetto, che
chiama anche il trigger della cancellazione di un indirizzo. Un soggetto senza natura non deve avere niente.

---

{% include-markdown "it/dbzero/anagrafiche/_indirizzi-obbligatori.md" %}

---

### ⚠️ Che cosa oggi non copre

* **Un soggetto rimasto incompleto non si modifica più.** Il requisito può cambiare senza che si scriva il
  soggetto: una riga della matrice che diventa obbligatoria, che entra nella sua validità, che si aggiunge.
  Nessuno rigiudica i soggetti che esistono; ma alla prima scrittura del soggetto, in qualunque colonna, il
  trigger lo giudica e lo rifiuta, finché nella stessa transazione non riceve l'indirizzo che manca.

---

### Codici errore

* `E_INDIRIZZO_OBBLIGATORIO_MANCANTE_TIPO_SOGGETTO` — manca un indirizzo che la natura chiede; lo solleva
  `anagrafiche.fn_guard_indirizzi_obbligatori_soggetto`, sul primo tipo mancante.

---

### Test

* `db/pgtap/anagrafiche/test-indirizzo-obbligatorio-mancante-frase-v1.sql` — il codice del livello soggetto e la
  frase intera, col tipo richiesto senza ripiego e col ripiego, su una riga obbligatoria costruita dal test.
* `db/pgtap/anagrafiche/test-indirizzi-obbligatori-ripiego-e-cancellazione-v1.sql` — il trigger che chiama il
  guard senza copie della regola, e la società che perde la sede legale.

---

### Note di migrazione

* 2026-11-17 — il controllo passa in `anagrafiche.fn_guard_indirizzi_obbligatori_soggetto`, condiviso col
  trigger della cancellazione di un indirizzo; il codice diventa proprio del livello soggetto, distinto da
  quello del ruolo, e la frase nomina natura e tipi per descrizione.

---

{% include-markdown "signature-core.md" %}
