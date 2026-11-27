## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_emittenti_fiscali_guard_codice_forma`

> **Ultimo aggiornamento**: 27 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali) — la sigla dell'emittente, unica e immutabile
>
> Approfondimento funzioni:
>
> * [script.fn_codice_normalizzato](/dbzero/script/funzioni/fn_codice_normalizzato) — la forma canonica di ogni codice
> * [script.trgfn_codice_maiuscolo](/dbzero/script/funzioni/trgfn_codice_maiuscolo) — il maiuscolo dei codici, montato dall'automazione
> * [vendite.fn_get_or_create_commessa](/dbzero/vendite/funzioni/fn_get_or_create_commessa) — compone il codice commessa con la sigla
> * [pagamenti.trgfn_vendite_contabili_gen_codice](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_gen_codice) — compone il codice della distinta d'incasso con la sigla

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_emittenti_fiscali_guard_codice_forma` dà una forma alla sigla dell'emittente: la porta al
maiuscolo e rifiuta una sigla che non sia fatta di sole maiuscole e cifre, da 2 a 10 caratteri.

---

### ⛔ Perché la sigla ha una forma

La sigla sta dentro i codici che il motore dei registri compone: la commessa è
`CMM-<sigla>-<anno>-<progressivo>`, la distinta d'incasso `DIS-<sigla>-<anno>-<progressivo>`. Quei codici si
leggono separando sul trattino, e una sigla col trattino dentro li renderebbe illeggibili. Il difetto sarebbe
muto: l'unicità dei codici reggerebbe, nessun errore, solo codici che non si leggono più, e per sempre, perché la
sigla non cambia.

---

### Il maiuscolo si applica, il resto si rifiuta

* **Il maiuscolo è la forma canonica**, non una scelta di chi scrive: `acme` diventa `ACME`, con la stessa
  normalizzazione di ogni codice (`script.fn_codice_normalizzato`).
* **Il resto non si aggiusta in silenzio.** Togliere il trattino da `AC-ME` darebbe `ACME`, una sigla che la
  persona non ha scritto: un identificatore è una scelta, e il guard la rifiuta con
  `E_EMITTENTE_CODICE_FORMA_NON_VALIDA`, col campo `codice` nel contesto per il form.
* **Si giudica la sigla già normalizzata.** In maiuscolo una sigla può allungarsi (`ß` diventa `SS`): dieci
  caratteri scritti possono diventarne undici, e il rifiuto è la frase del guard, non il CHECK; una sigla che in
  maiuscolo supera la colonna (`varchar(32)`) darebbe un errore di lunghezza. Una sigla vuota o assente è
  rifiutata dallo stesso codice.

Scatta alla creazione e a ogni modifica che nomina la sigla, nella fascia `a05`, prima del lock di colonna:
riscrivere `acme` su un emittente `ACME` arriva al lock come lo stesso valore, e passa. Il CHECK
`chk_emittenti_fiscali_codice_forma` dice la stessa forma, ed è la rete per le strade che il trigger non percorre.

---

### Il maiuscolo si fa due volte, ed è voluto

Dopo questo guard, `script.trgfn_codice_maiuscolo` (fascia `a15`, montato dall'automazione su ogni tabella con un
codice) rinormalizza la sigla, che trova già nella forma canonica. Non è una regola in due copie: tutti e due
usano `script.fn_codice_normalizzato`. Questo guard deve giudicare il valore già normalizzato, prima del CHECK;
l'`a15` copre ogni colonna codice della tabella, e su un valore canonico non cambia niente.

---

### Codici errore

* `E_EMITTENTE_CODICE_FORMA_NON_VALIDA` — la sigla, in maiuscolo, non è di 2-10 maiuscole e cifre; il segnaposto
  è la sigla normalizzata.

---

### Test

* `db/pgtap/anagrafiche/test-emittenti-fiscali-codice-forma.sql` — il CHECK e il trigger montati; i rifiuti
  della sigla col trattino, di un carattere, di undici, e di quella che si allunga in maiuscolo; la sigla
  conforme e quella in minuscolo, che passa alzata; le sigle esistenti, tutte conformi.

---

### Note di migrazione

* 2026-08-31 — nasce, quando la sigla entra nel codice commessa.
* 2026-11-04 — il maiuscolo passa per la forma canonica comune dei codici, e la sigla si giudica dopo averla
  normalizzata.

---

{% include-markdown "signature-core.md" %}
