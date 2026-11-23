## 📘 Documentazione Concettuale – Funzione `magazzino.fn_crea_ubicazione`

> **Ultimo aggiornamento**: 23 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.ubicazioni](/dbzero/magazzino/tabelle/ubicazioni) — la tabella in cui scrive la riga
>
> Approfondimento funzioni:
>
> * [magazzino.fn_ubicazioni_colonne_ammesse](/dbzero/magazzino/funzioni/fn_ubicazioni_colonne_ammesse) — le colonne facoltative che accetta
> * [magazzino.fn_aggiungi_ubicazione](/dbzero/magazzino/funzioni/fn_aggiungi_ubicazione) — il verbo dell'operatore, che lo chiama dopo il permesso
> * [dbops.fn_pgtap_crea_ubicazione](/dbzero/dbops/funzioni/fn_pgtap_crea_ubicazione) — la fixture dei test, che passa dal verbo
> * [script.fn_scrivi_riga_da_jsonb](/dbzero/script/funzioni/fn_scrivi_riga_da_jsonb) — la scrittura della riga

---

### 🎯 Scopo Principale

**Far nascere un'ubicazione** in una sola istruzione: la sede unica della creazione, che usano il verbo dell'operatore e, senza un operatore, il provisioning dei dati di sviluppo.

---

### Regole

Il magazzino, il codice e il tipo sono obbligatori; il magazzino è l'identità della nascita e poi non cambia. Un'ubicazione nasce attiva.

Gli altri campi sono facoltativi e devono stare nella lista «crea»: uno sconosciuto è rifiutato col suo nome. Un campo assente, o mandato vuoto, prende il valore di default.

---

### Che cosa non controlla

Il permesso: lo controlla chi lo chiama, cioè il verbo di nascita. Che l'ubicazione padre sia dello stesso magazzino, che padre e tipo siano attivi, che il codice sia unico nel magazzino e che il magazzino sia dell'azienda: lo dicono i controlli della tabella.

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
