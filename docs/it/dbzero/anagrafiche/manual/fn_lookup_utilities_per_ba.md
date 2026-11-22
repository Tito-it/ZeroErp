## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_lookup_utilities_per_ba`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — il billing account di cui si cercano le utility
> * [config.utilities_tipi_ruolo](/dbzero/config/tabelle/utilities_tipi_ruolo) — quali utility sono ammesse per quale tipo di ruolo
> * [anagrafiche.emittenti_fiscali_utilities](/dbzero/anagrafiche/tabelle/emittenti_fiscali_utilities) — i parametri d'importo propri di un'azienda
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_get_emittente_fiscale_pk](/dbzero/anagrafiche/funzioni/fn_get_emittente_fiscale_pk) — l'azienda del billing account
> * [script.fn_get_ba_emittente_sr_id](/dbzero/script/funzioni/fn_get_ba_emittente_sr_id) — la regola a tre livelli dietro quella risposta
> * [anagrafiche.fn_parametri_importo_utility](/dbzero/anagrafiche/funzioni/fn_parametri_importo_utility) — i parametri d'importo effettivi

---

### 🎯 Scopo Principale

`anagrafiche.fn_lookup_utilities_per_ba` restituisce le utility proponibili per un billing account: quelle
ammesse sia per il tipo di ruolo indicato sia per l'azienda che fattura il billing account, ciascuna coi suoi
parametri d'importo effettivi.

---

### Due ammissioni, nello stesso giorno

Una utility esce se in `config.utilities_tipi_ruolo` è ammessa, con una riga attiva e valida nel giorno
operativo:

* per il **tipo di ruolo** passato da chi chiama (`p_ruolo_codice_soggetto`, un codice interno come `CL`, `FO`,
  `GE`);
* per il tipo di ruolo **emittente** (`EF`).

Tutti e due i tipi si cercano per codice interno, che non cambia. Un codice che non esiste, o che non ha
utility ammesse, dà zero righe e non un errore.

---

### L'azienda del billing account

L'azienda si risolve con `fn_get_emittente_fiscale_pk`, cioè con la regola a tre livelli: il collegamento del
billing account; senza, in sessione, l'azienda di chi agisce; senza sessione, l'azienda predefinita. Se nessuno
dei tre risponde, `E_EMITTENTE_DEFAULT_MISSING`. L'azienda decide i parametri, non l'elenco: l'elenco lo fa la
matrice dei tipi di ruolo.

---

### I parametri effettivi

Per ogni utility i parametri vengono da `fn_parametri_importo_utility`:

* i **decimali** dalla riga dell'azienda per quella utility, se c'è, altrimenti dall'utility;
* il **metodo di arrotondamento** dalla riga dell'azienda, poi dalla politica generale dell'azienda, poi
  dall'utility;
* le **soglie minime** solo dalla riga dell'azienda: senza riga sono vuote;
* `is_personalizzata_per_ef` dice se la riga dell'azienda c'è.

Una utility ammessa senza la riga dell'azienda resta nell'elenco, coi valori di sistema.

---

### ⚠️ Che cosa oggi non copre

* **Il ruolo non lo legge dal billing account.** Il tipo di ruolo lo dice chi chiama, e la funzione non
  verifica che sia quello del ruolo del billing account: un codice diverso dà l'elenco di un altro tipo di
  ruolo senza errore.
* **Il billing account non deve esistere.** Un id positivo che non corrisponde a nessun billing account non è
  rifiutato: senza collegamento, l'azienda si risolve dalla sessione o dalla predefinita, e la funzione risponde
  con le utility di quell'azienda.

---

### Codici errore

* `E_PARAMETRO_INVALIDO` — billing account mancante o non positivo, o tipo di ruolo vuoto.
* `E_EMITTENTE_DEFAULT_MISSING` — da `fn_get_emittente_fiscale_pk`: nessuna azienda risolvibile.

---

### Test

* `db/pgtap/anagrafiche/test-fn-lookup-utilities-per-ba.sql` — i parametri obbligatori, la riga
  personalizzata, l'utility ammessa per cliente ed emittente, la risoluzione per codice interno anche quando il
  codice visibile del tipo di ruolo cambia.
* `db/pgtap/vendite/test-parametri-importo-utility-v1.sql` — il lookup mostra i parametri effettivi, mai vuoti.

---

### Note di migrazione

* 2026-06-29 — i tipi di ruolo si cercano per codice interno: col codice visibile la funzione rispondeva zero
  righe.
* 2026-10-21 — i parametri d'importo sono quelli effettivi: prima, senza la riga dell'azienda, uscivano vuoti.

---

{% include-markdown "signature-core.md" %}
