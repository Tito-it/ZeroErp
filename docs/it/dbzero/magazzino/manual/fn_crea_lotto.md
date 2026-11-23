## 📘 Documentazione Concettuale – Funzione `magazzino.fn_crea_lotto`

> **Ultimo aggiornamento**: 23 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.lotti](/dbzero/magazzino/tabelle/lotti) — la tabella in cui scrive la riga
>
> Approfondimento funzioni:
>
> * [magazzino.fn_lotti_colonne_ammesse](/dbzero/magazzino/funzioni/fn_lotti_colonne_ammesse) — le colonne facoltative che accetta
> * [magazzino.fn_aggiungi_lotto](/dbzero/magazzino/funzioni/fn_aggiungi_lotto) — il verbo dell'operatore, che lo chiama dopo il permesso
> * [dbops.fn_pgtap_crea_lotto_di_magazzino](/dbzero/dbops/funzioni/fn_pgtap_crea_lotto_di_magazzino) — la fixture dei test, che passa dal verbo
> * [script.fn_scrivi_riga_da_jsonb](/dbzero/script/funzioni/fn_scrivi_riga_da_jsonb) — la scrittura della riga

---

### 🎯 Scopo Principale

**Far nascere un lotto di magazzino** in una sola istruzione: la sede unica della creazione, che usano il verbo dell'operatore e, senza un operatore, il provisioning dei dati di sviluppo.

---

### Regole

L'articolo, il codice e la data di arrivo sono obbligatori; l'articolo è l'identità della nascita. Un lotto nasce attivo, e l'azienda non si sceglie: la mette la sessione.

Gli altri campi sono facoltativi e devono stare nella lista «crea»: uno sconosciuto è rifiutato col suo nome. Un campo assente, o mandato vuoto, prende il valore di default.

---

### Che cosa non controlla

Il permesso: lo controlla chi lo chiama, cioè il verbo di nascita. Che l'articolo sia attivo, che la scadenza non venga prima dell'arrivo, che il codice sia unico per azienda e articolo e che il lotto stia nel perimetro dell'azienda: lo dicono i controlli della tabella.

---

### Codici errore

* `E_CAMPO_NON_AMMESSO` — fra i campi facoltativi ce n'è uno fuori lista; il codice lo nomina.
* `E_SCRIPT_CHIAMATA_NON_VALIDA` — i campi facoltativi non sono un oggetto: chi chiama è rotto.

---

### Test

`db/pgtap/magazzino/test-colonne-ammesse-e-nascita-anagrafiche-v1.sql`.

---

### Note di migrazione

* 2026-11-22 — nasce sullo stampo di `magazzino.fn_crea_magazzino`, quando le anagrafiche di magazzino passano dai verbi (`brief-db-magazzino-tutte-le-scritture-dal-verbo`).

---

{% include-markdown "signature-core.md" %}
