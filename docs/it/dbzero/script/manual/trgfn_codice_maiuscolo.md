## 📘 Documentazione Concettuale – Funzione `script.trgfn_codice_maiuscolo`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automazione_codice_eccezioni](/dbzero/dbops/tabelle/automazione_codice_eccezioni) — le colonne dove non si monta
>
> Approfondimento funzioni:
>
> * [dbops.fn_run_automations_codice_maiuscolo](/dbzero/dbops/funzioni/fn_run_automations_codice_maiuscolo) — chi la monta
> * [dbops.fn_codice_maiuscolo_perimetro](/dbzero/dbops/funzioni/fn_codice_maiuscolo_perimetro) — dove è dovuta
> * [script.trgfn_lock_columns](/dbzero/script/funzioni/trgfn_lock_columns) — il lucchetto che non deve scattare a vuoto
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — §4.8, l'automazione CODICE_MAIUSCOLO
> * [Linee guida Trigger](/linee-guida-trigger) — fasi e `UPDATE OF`

---

### 🎯 Scopo Principale

Salva il codice di una riga in **maiuscolo e senza spazi ai bordi**. Un codice che l'operatore
digita è un identificativo e non distingue le maiuscole: `VITE-M8` e `vite-m8` sono lo stesso
articolo. Con il valore normalizzato, l'indice `UNIQUE` che la colonna ha già diventa un'unicità
senza distinzione di maiuscole, e nessuna ricerca deve ripetere un `upper()`.

Non si monta a mano: la monta l'automazione CODICE_MAIUSCOLO su ogni colonna `codice` dell'ambito,
tranne le eccezioni.

---

### Tre scelte

* **`BEFORE INSERT OR UPDATE`, senza `OF codice`.** Il codice lo scrivono anche altri trigger
  `BEFORE`: i generatori `a10_gen_codice` lo valorizzano quando arriva vuoto, e un `OF codice` non
  scatterebbe sulle loro scritture.
* **Fase `a15`**, dopo i guard e i generatori `a10`: anche un codice generato si salva normalizzato.
  Il guard di forma degli emittenti fiscali (`a05`) normalizza da sé prima di validare, e parla
  prima.
* **Un `UPDATE` che non cambia il codice non lo tocca.** Un salvataggio che riscrive tutta la riga
  non è una modifica del codice: su una tabella col lucchetto di colonna sarebbe un
  `E_CODICE_NON_MODIFICABILE` senza che l'operatore abbia cambiato niente.

`NULL` resta `NULL`.

---

### ⚠️ Chi rilegge per valore

Il valore salvato può essere diverso da quello scritto. Chi scrive un codice e poi lo **ricerca per
valore** deve ricomporlo in maiuscolo, oppure leggere quello salvato (`RETURNING codice`). Vale per
i «trova per codice» che confrontano l'input dell'utente (linee-guida-sql §8.4) e per le fixture che
costruiscono un codice con un suffisso esadecimale.

---

### Test

`db/pgtap/dbops/test-codice-maiuscolo-v1.sql`: inserimento normalizzato (test 13), unicità senza
maiuscole (14), riscrittura uguale intatta (15), modifica normalizzata (16), `NULL` (17), codice
generato da un `a10` (18).

---

{% include-markdown "signature-core.md" %}
