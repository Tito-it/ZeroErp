## 📘 Documentazione Concettuale – Funzione `magazzino.fn_crea_asset`

> **Ultimo aggiornamento**: 23 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.assets](/dbzero/magazzino/tabelle/assets) — la tabella in cui scrive la riga
>
> Approfondimento funzioni:
>
> * [magazzino.fn_assets_colonne_ammesse](/dbzero/magazzino/funzioni/fn_assets_colonne_ammesse) — le colonne facoltative che accetta
> * [magazzino.fn_aggiungi_asset](/dbzero/magazzino/funzioni/fn_aggiungi_asset) — il verbo dell'operatore, che lo chiama dopo il permesso
> * [dbops.fn_pgtap_crea_asset](/dbzero/dbops/funzioni/fn_pgtap_crea_asset) — la fixture dei test, che passa dal verbo
> * [script.fn_scrivi_riga_da_jsonb](/dbzero/script/funzioni/fn_scrivi_riga_da_jsonb) — la scrittura della riga

---

### 🎯 Scopo Principale

**Far nascere un seriale** in una sola istruzione: la sede unica della creazione, che usano il verbo dell'operatore e, senza un operatore, il provisioning dei dati di sviluppo.

---

### Regole

L'articolo, il seriale, lo stato e la proprietà sono obbligatori. Un seriale nasce attivo; dove si trova lo dice il registro dei movimenti, non la riga. L'azienda, se non la si indica, è quella della sessione; se la si indica, deve essere nel perimetro.

Gli altri campi sono facoltativi e devono stare nella lista «crea»: uno sconosciuto è rifiutato col suo nome. Un campo assente, o mandato vuoto, prende il valore di default.

---

### Che cosa non controlla

Il permesso: lo controlla chi lo chiama, cioè il verbo di nascita. Che articolo, stato, proprietà e azienda siano attivi, che il seriale sia unico e che il cliente legato sia dell'azienda: lo dicono i controlli della tabella.

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
