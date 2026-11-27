## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_lookup_utilities_per_ba`

> **Ultimo aggiornamento**: 27 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — il billing account di cui si cercano le utility
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il ruolo del billing account, da cui si legge il tipo
> * [config.utilities_tipi_ruolo](/dbzero/config/tabelle/utilities_tipi_ruolo) — quali utility sono ammesse per quale tipo di ruolo
> * [anagrafiche.emittenti_fiscali_utilities](/dbzero/anagrafiche/tabelle/emittenti_fiscali_utilities) — le utility che un'azienda gestisce, coi suoi parametri
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_get_emittente_fiscale_pk](/dbzero/anagrafiche/funzioni/fn_get_emittente_fiscale_pk) — l'azienda del billing account
> * [script.fn_get_ba_emittente_sr_id](/dbzero/script/funzioni/fn_get_ba_emittente_sr_id) — la regola dietro quella risposta: il collegamento del billing account
> * [anagrafiche.fn_utilities_emittente](/dbzero/anagrafiche/funzioni/fn_utilities_emittente) — le utility di un'azienda: ammesse, gestite, coi parametri
> * [anagrafiche.fn_parametri_importo_utility](/dbzero/anagrafiche/funzioni/fn_parametri_importo_utility) — i parametri d'importo effettivi

---

### 🎯 Scopo Principale

`anagrafiche.fn_lookup_utilities_per_ba` restituisce le utility proponibili per un billing account: quelle che
l'azienda del billing account **gestisce**, ammesse per il tipo di ruolo indicato, ciascuna coi suoi parametri
d'importo effettivi. La regola non sta qui: è di `anagrafiche.fn_utilities_emittente`, di cui la funzione tiene
le righe gestite.

---

### Che cosa esce

Una utility esce se:

* l'azienda del billing account la **gestisce**: ha la sua riga in `anagrafiche.emittenti_fiscali_utilities` ed
  è accesa. Un'utility che l'azienda non gestisce non si propone, perché il billing account non nascerebbe;
* in `config.utilities_tipi_ruolo` è ammessa, con una riga attiva e valida nel giorno operativo, per il **tipo di
  ruolo** del billing account (`p_ruolo_codice_soggetto`, un codice interno come `CL`, `FO`, `GE`) e per il tipo
  di ruolo **emittente** (`EF`).

Un tipo di ruolo che non ha utility dà zero righe e non un errore.

---

### ⛔ Il billing account e il suo ruolo si leggono, non si credono

La funzione legge il billing account e il tipo del suo ruolo prima di rispondere:

* un id che non è un billing account, o che chi chiama non vede (la funzione gira coi suoi permessi), è
  rifiutato: non ricade sull'azienda predefinita;
* un tipo di ruolo che non è quello del billing account è rifiutato: l'elenco di un altro tipo di ruolo non
  sarebbe proponibile per quel conto.

Il primo risponde `E_BILLING_ACCOUNT_NOT_FOUND`: la cosa indicata non esiste, per chi chiama. Il secondo
risponde `E_PARAMETRO_INVALIDO`, come un parametro mancante: è chi chiama a sbagliare. Il parametro del ruolo
resta nella firma, che il backend chiama per posizione.

---

### L'azienda del billing account

L'azienda si risolve con `anagrafiche.fn_get_emittente_fiscale_pk`: è quella del collegamento del billing
account, che ogni billing account ha. L'azienda decide l'elenco (le utility che gestisce) e i parametri; la
matrice dei tipi di ruolo restringe l'elenco al ruolo del billing account.

---

### I parametri effettivi

Per ogni utility i parametri vengono da `fn_parametri_importo_utility`:

* i **decimali** dalla riga dell'azienda per quella utility, se c'è, altrimenti dall'utility;
* il **metodo di arrotondamento** dalla riga dell'azienda, poi dalla politica generale dell'azienda, poi
  dall'utility;
* le **soglie minime** solo dalla riga dell'azienda: senza riga sono vuote;
* `is_personalizzata_per_ef` dice se la riga dell'azienda porta almeno un parametro.

Una utility gestita senza parametri resta nell'elenco, coi valori di sistema.

---

### Codici errore

* `E_PARAMETRO_INVALIDO` — billing account mancante o non positivo; tipo di ruolo vuoto o diverso da quello del
  billing account.
* `E_BILLING_ACCOUNT_NOT_FOUND` — l'id non è un billing account, o è fuori dal perimetro di chi chiama.
* `E_EMITTENTE_DEFAULT_MISSING` — da `anagrafiche.fn_get_emittente_fiscale_pk`: nessuna azienda risolvibile.

---

### Test

* `db/pgtap/anagrafiche/test-fn-lookup-utilities-per-ba.sql` — i parametri obbligatori, la riga
  personalizzata, l'utility ammessa per cliente ed emittente, la risoluzione per codice interno anche quando il
  codice visibile del tipo di ruolo cambia.
* `db/pgtap/anagrafiche/test-fn-lookup-utilities-per-ba-legge-il-ba-v1.sql` — l'id che non è un billing account
  e il ruolo che non è il suo sono rifiutati; col ruolo del billing account la funzione risponde.
* `db/pgtap/vendite/test-parametri-importo-utility-v1.sql` — il lookup mostra i parametri effettivi, mai vuoti.

---

### Note di migrazione

* 2026-06-29 — i tipi di ruolo si cercano per codice interno: col codice visibile la funzione rispondeva zero
  righe.
* 2026-10-21 — i parametri d'importo sono quelli effettivi: prima, senza la riga dell'azienda, uscivano vuoti.
* 2026-11-26 — legge il billing account: prima un id che non era un billing account ricadeva sulla predefinita,
  e un tipo di ruolo diverso dava l'elenco di un altro ruolo, senza errore.

---

{% include-markdown "signature-core.md" %}
